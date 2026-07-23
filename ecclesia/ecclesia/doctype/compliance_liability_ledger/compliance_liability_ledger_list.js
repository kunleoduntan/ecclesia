// ecclesia/public/js/compliance_liability_ledger_list.js

frappe.listview_settings['Compliance Liability Ledger'] = {
    add_fields: [
        "name", "ledger_key", "obligation_type", "period_label", "company",
        "total_liability", "total_allocated", "balance_due", "status",
        "due_date", "is_overdue", "fiscal_year"
    ],

    get_indicator: function(doc) {
        if (doc.status === "Fully Paid")
            return [__("Fully Paid"), "green", "status,=,Fully Paid"];
        if (doc.status === "Partially Paid")
            return [__("Partially Paid"), "orange", "status,=,Partially Paid"];
        if (doc.status === "Overdue")
            return [__("Overdue"), "red", "status,=,Overdue"];
        if (doc.status === "Open")
            return [__("Open"), "blue", "status,=,Open"];
        if (doc.status === "Reconciled")
            return [__("Reconciled"), "purple", "status,=,Reconciled"];
        return [__("Unknown"), "grey", "status,=,"];
    },

    formatters: {
        ledger_key: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#1e3a5f;">
                <i class="fa fa-book" style="color:#3b82f6;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        obligation_type: function(v) {
            if (!v) return '';
            const colors = {
                'VAT': '#3b82f6',
                'WHT': '#f59e0b',
                'PAYE': '#10b981',
                'Pension': '#8b5cf6',
                'NHF': '#ec4899',
                'NSITF': '#f97316',
                'ITF': '#14b8a6',
                'CIT': '#6366f1',
                'Stamp Duty': '#8b5cf6',
                'Capital Gains Tax': '#f472b6'
            };
            const icons = {
                'VAT': 'fa-shopping-cart',
                'WHT': 'fa-percent',
                'PAYE': 'fa-users',
                'Pension': 'fa-university',
                'NHF': 'fa-home',
                'NSITF': 'fa-shield',
                'ITF': 'fa-graduation-cap',
                'CIT': 'fa-building-o',
                'Stamp Duty': 'fa-stamp',
                'Capital Gains Tax': 'fa-line-chart'
            };
            return `<span style="background:${colors[v] || '#475569'};color:white;padding:3px 12px;border-radius:12px;font-size:10px;font-weight:600;display:inline-block;">
                <i class="fa ${icons[v] || 'fa-tag'}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        status: function(v) {
            if (!v) return '';
            const colors = {
                'Fully Paid': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-circle' },
                'Partially Paid': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-hourglass-half' },
                'Overdue': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-exclamation-triangle' },
                'Open': { bg: '#DBEAFE', text: '#1E40AF', icon: 'fa-folder-open-o' },
                'Reconciled': { bg: '#F3E8FF', text: '#6B21A8', icon: 'fa-check-double' },
                'Exempt': { bg: '#F1F5F9', text: '#475569', icon: 'fa-ban' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;display:inline-block;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        total_liability: function(v) {
            if (v === null || v === undefined) return '';
            return `<span style="color:#1e3a8a;font-weight:600;">${frappe.format(v, {fieldtype: 'Currency'})}</span>`;
        },
        total_allocated: function(v) {
            if (v === null || v === undefined) return '';
            return `<span style="color:#059669;font-weight:600;">${frappe.format(v, {fieldtype: 'Currency'})}</span>`;
        },
        balance_due: function(v) {
            if (v === null || v === undefined) return '';
            return v > 0 
                ? `<span style="color:#dc2626;font-weight:700;">${frappe.format(v, {fieldtype: 'Currency'})}</span>`
                : `<span style="color:#059669;font-weight:600;">${frappe.format(v, {fieldtype: 'Currency'})}</span>`;
        },
        due_date: function(v) {
            if (!v) return '';
            let today = frappe.datetime.get_today();
            let diff = frappe.datetime.get_diff(v, today);
            let color = diff < 0 ? '#dc2626' : (diff < 7 ? '#f59e0b' : '#475569');
            let icon = diff < 0 ? 'fa-hourglass-end' : 'fa-calendar';
            return `<span style="color:${color};">
                <i class="fa ${icon}" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}
            </span>`;
        },
        is_overdue: function(v) {
            return v 
                ? `<span style="color:#dc2626;font-weight:700;">🔴 Overdue</span>`
                : `<span style="color:#059669;">✅ On Time</span>`;
        }
    },

    onload: function(listview) {
        window._cll_listview = listview;
        setTimeout(() => {
            add_cll_styles();
            add_cll_summary_cards(listview);
            add_cll_quick_filters(listview);
            // Load summary data after cards are added
            load_cll_summary_data(listview);
        }, 500);
        add_cll_export_options(listview);
    },

    refresh: function(listview) {
        window._cll_listview = listview;
        setTimeout(() => {
            // Refresh summary data
            load_cll_summary_data(listview);
            update_cll_filter_counts();
        }, 300);
    },

    primary_action: () => frappe.new_doc("Compliance Liability Ledger"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_cll_row_actions(doc)
    },

    colwidths: {
        "ledger_key": 180, "obligation_type": 120, "period_label": 100,
        "company": 160, "total_liability": 130, "total_allocated": 130,
        "balance_due": 130, "status": 130, "due_date": 120,
        "is_overdue": 100, "fiscal_year": 100
    }
};

// Global variable to store summary data
let _cll_summary_data = null;

function load_cll_summary_data(listview) {
    // Get current filters
    let filters = {};
    try {
        if (listview && listview.filter_area) {
            const current = listview.filter_area.get() || [];
            current.forEach(f => { 
                if (f[0] === 'Compliance Liability Ledger') filters[f[1]] = f[3]; 
            });
        }
    } catch (e) {
        console.warn('Could not get filters:', e);
    }
    
    // Call the server method from the Python file
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.compliance_liability_ledger.compliance_liability_ledger_list.get_cll_summary',
        args: { 
            filters: JSON.stringify(filters)
        },
        callback: function(r) {
            if (r.message) {
                // Store the summary data
                _cll_summary_data = r.message;
                
                // Update UI with the data
                update_cll_summary_cards_from_data();
                update_cll_filter_counts_from_data();
            } else {
                console.warn('No summary data returned from server');
                // Set default values
                _cll_summary_data = {
                    total_count: 0,
                    total_liability: 0,
                    paid_count: 0,
                    partial_count: 0,
                    overdue_count: 0,
                    open_count: 0,
                    reconciled_count: 0,
                    vat_count: 0,
                    wht_count: 0,
                    paye_count: 0,
                    pension_count: 0
                };
                update_cll_summary_cards_from_data();
                update_cll_filter_counts_from_data();
            }
        },
        error: function(err) {
            console.error('Error loading summary data:', err);
            // Set default values on error
            _cll_summary_data = {
                total_count: 0,
                total_liability: 0,
                paid_count: 0,
                partial_count: 0,
                overdue_count: 0,
                open_count: 0,
                reconciled_count: 0,
                vat_count: 0,
                wht_count: 0,
                paye_count: 0,
                pension_count: 0
            };
            update_cll_summary_cards_from_data();
            update_cll_filter_counts_from_data();
        }
    });
}

function update_cll_summary_cards_from_data() {
    if (!_cll_summary_data) {
        console.warn('No summary data available');
        return;
    }
    
    const d = _cll_summary_data;
    console.log('Updating summary cards with data:', d);
    
    // Update total liability with proper currency formatting
    const totalLiabElement = document.getElementById('cll-total-liability');
    if (totalLiabElement) {
        const totalAmount = d.total_liability || 0;
        const formattedValue = frappe.format(totalAmount, {fieldtype: 'Currency'});
        totalLiabElement.textContent = formattedValue;
        totalLiabElement.style.display = 'block';
    }
    
    // Update count cards
    const paidElement = document.getElementById('cll-paid');
    if (paidElement) paidElement.textContent = d.paid_count || 0;
    
    const partialElement = document.getElementById('cll-partial');
    if (partialElement) partialElement.textContent = d.partial_count || 0;
    
    const overdueElement = document.getElementById('cll-overdue');
    if (overdueElement) overdueElement.textContent = d.overdue_count || 0;
    
    const openElement = document.getElementById('cll-open');
    if (openElement) openElement.textContent = d.open_count || 0;
}

function update_cll_filter_counts_from_data() {
    if (!_cll_summary_data) {
        console.warn('No summary data available for filter counts');
        return;
    }
    
    const d = _cll_summary_data;
    
    // Update filter chip counts
    const allChip = document.querySelector('.filter-chip[data-filter="all"] .count');
    if (allChip) allChip.textContent = d.total_count || 0;
    
    const overdueChip = document.querySelector('.filter-chip[data-filter="overdue"] .count');
    if (overdueChip) overdueChip.textContent = d.overdue_count || 0;
    
    const paidChip = document.querySelector('.filter-chip[data-filter="paid"] .count');
    if (paidChip) paidChip.textContent = d.paid_count || 0;
    
    const partialChip = document.querySelector('.filter-chip[data-filter="partial"] .count');
    if (partialChip) partialChip.textContent = d.partial_count || 0;
    
    const openChip = document.querySelector('.filter-chip[data-filter="open"] .count');
    if (openChip) openChip.textContent = d.open_count || 0;
    
    const vatChip = document.querySelector('.filter-chip[data-filter="vat"] .count');
    if (vatChip) vatChip.textContent = d.vat_count || 0;
    
    const payeChip = document.querySelector('.filter-chip[data-filter="paye"] .count');
    if (payeChip) payeChip.textContent = d.paye_count || 0;
}

function show_cll_row_actions(doc) {
    const actions = [
        { label: '📊 View Ledger', action: () => frappe.set_route('Form', 'Compliance Liability Ledger', doc.name) },
        { label: '💰 View Allocations', action: () => frappe.set_route('Form', 'Compliance Liability Ledger', doc.name, {'tab': 'tab_allocations'}) },
        { label: '📋 View Sources', action: () => frappe.set_route('Form', 'Compliance Liability Ledger', doc.name, {'tab': 'tab_sources'}) },
        { label: '🔄 Reconcile', action: () => reconcile_cll(doc) }
    ];
    show_actions_menu(actions);
}

function reconcile_cll(doc) {
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Compliance Liability Ledger', name: doc.name },
        callback: function(r) {
            if (r.message) {
                frappe.set_route('Form', 'Compliance Liability Ledger', doc.name);
                frappe.msgprint({
                    title: __('Reconciliation'),
                    message: __('This CLL has a balance of {0}. Please review allocations.', [
                        frappe.format(r.message.balance_due, {fieldtype: 'Currency'})
                    ])
                });
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

function add_cll_styles() {
    if ($('#cll-styles').length) return;
    $('head').append(`
        <style id="cll-styles">
        .list-row {
            transition: all .25s ease !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            margin: 2px 0 !important;
        }
        .list-row:hover {
            background: linear-gradient(90deg, #e0f2fe, #bae6fd) !important;
            border-left-color: #3b82f6 !important;
            transform: translateX(3px);
        }
        .list-headers {
            background: linear-gradient(135deg, #1e40af, #3b82f6) !important;
            color: #fff !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            font-size: 11px !important;
            letter-spacing: .8px !important;
            padding: 14px 16px !important;
            border-radius: 12px !important;
        }
        .cll-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            padding: 20px;
            margin: 16px 16px 20px 16px;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #f0f0f0;
        }
        .summary-card {
            padding: 20px 16px;
            border-radius: 12px;
            text-align: center;
            border: 2px solid transparent;
            transition: all .3s ease;
            cursor: default;
            position: relative;
            overflow: hidden;
            min-height: 100px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .summary-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,.12);
        }
        .summary-card.total {
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
            border-color: #93c5fd;
        }
        .summary-card.total .summary-card-label { color: #1d4ed8; }
        .summary-card.total .summary-card-value { color: #1e3a8a; font-size: 28px; font-weight: 800; }
        .summary-card.overdue {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.overdue .summary-card-label { color: #b91c1c; }
        .summary-card.overdue .summary-card-value { color: #991b1b; }
        .summary-card.paid {
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            border-color: #6ee7b7;
        }
        .summary-card.paid .summary-card-label { color: #047857; }
        .summary-card.paid .summary-card-value { color: #065f46; }
        .summary-card.partial {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.partial .summary-card-label { color: #b45309; }
        .summary-card.partial .summary-card-value { color: #92400e; }
        .summary-card.open {
            background: linear-gradient(135deg, #f5f3ff, #ede9fe);
            border-color: #c4b5fd;
        }
        .summary-card.open .summary-card-label { color: #5b21b6; }
        .summary-card.open .summary-card-value { color: #5b21b6; }
        .summary-card-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: .8px;
            font-weight: 700;
            margin-bottom: 6px;
            position: relative;
            z-index: 1;
        }
        .summary-card-value {
            font-size: 24px;
            font-weight: 800;
            position: relative;
            z-index: 1;
            line-height: 1.2;
            display: block !important;
        }
        .summary-card-sub {
            font-size: 10px;
            color: #64748b;
            margin-top: 4px;
            position: relative;
            z-index: 1;
        }
        .summary-card .card-icon {
            font-size: 24px;
            margin-bottom: 6px;
            opacity: 0.7;
        }
        .cll-filters {
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
            box-shadow: 0 4px 12px rgba(99,102,241,.15);
        }
        .filter-chip.active {
            background: linear-gradient(135deg, #4338ca, #6366f1);
            color: #fff;
            border-color: #6366f1;
            box-shadow: 0 4px 14px rgba(99,102,241,.3);
            font-weight: 600;
        }
        .filter-chip .count {
            background: rgba(255,255,255,.25);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
            min-width: 22px;
            text-align: center;
        }
        .filter-chip.active .count {
            background: rgba(255,255,255,.35);
        }
        </style>
    `);
}

function add_cll_summary_cards(listview) {
    // Remove existing summary cards
    $('.cll-summary').remove();
    
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    // Create summary cards with proper structure
    const summaryHTML = `
        <div class="cll-summary">
            <div class="summary-card total">
                <div class="card-icon">💰</div>
                <div class="summary-card-label">Total Liability</div>
                <div class="summary-card-value" id="cll-total-liability">₦0.00</div>
                <div class="summary-card-sub">All obligations</div>
            </div>
            <div class="summary-card paid">
                <div class="card-icon">✅</div>
                <div class="summary-card-label">Fully Paid</div>
                <div class="summary-card-value" id="cll-paid">0</div>
                <div class="summary-card-sub">Settled obligations</div>
            </div>
            <div class="summary-card partial">
                <div class="card-icon">⏳</div>
                <div class="summary-card-label">Partially Paid</div>
                <div class="summary-card-value" id="cll-partial">0</div>
                <div class="summary-card-sub">In progress</div>
            </div>
            <div class="summary-card overdue">
                <div class="card-icon">🚨</div>
                <div class="summary-card-label">Overdue</div>
                <div class="summary-card-value" id="cll-overdue">0</div>
                <div class="summary-card-sub">Past due date</div>
            </div>
            <div class="summary-card open">
                <div class="card-icon">📋</div>
                <div class="summary-card-label">Open</div>
                <div class="summary-card-value" id="cll-open">0</div>
                <div class="summary-card-sub">Awaiting payment</div>
            </div>
        </div>
    `;
    
    pageContent.prepend(summaryHTML);
}

function update_cll_summary_cards(listview) {
    // Refresh data and update
    load_cll_summary_data(listview);
}

function add_cll_quick_filters(listview) {
    $('.cll-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['overdue', 'fa-exclamation-triangle', 'Overdue'],
        ['paid', 'fa-check-circle', 'Fully Paid'],
        ['partial', 'fa-hourglass-half', 'Partially Paid'],
        ['open', 'fa-folder-open-o', 'Open'],
        ['vat', 'fa-shopping-cart', 'VAT'],
        ['paye', 'fa-users', 'PAYE']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyCLLFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    if (pageContent.length) {
        pageContent.prepend(`<div class="cll-filters">${chips}</div>`);
        // Update filter counts with existing data if available
        if (_cll_summary_data) {
            update_cll_filter_counts_from_data();
        }
    }
}

window.applyCLLFilter = function(filter, el) {
    const listview = window._cll_listview || cur_list;
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
    
    if (filter === 'overdue') {
        listview.filter_area.add('Compliance Liability Ledger', 'status', '=', 'Overdue');
    } else if (filter === 'paid') {
        listview.filter_area.add('Compliance Liability Ledger', 'status', '=', 'Fully Paid');
    } else if (filter === 'partial') {
        listview.filter_area.add('Compliance Liability Ledger', 'status', '=', 'Partially Paid');
    } else if (filter === 'open') {
        listview.filter_area.add('Compliance Liability Ledger', 'status', '=', 'Open');
    } else if (filter === 'vat') {
        listview.filter_area.add('Compliance Liability Ledger', 'obligation_type', '=', 'VAT');
    } else if (filter === 'paye') {
        listview.filter_area.add('Compliance Liability Ledger', 'obligation_type', '=', 'PAYE');
    }
    // 'all' filter - no filter applied
    
    listview.refresh();
};

function update_cll_filter_counts() {
    // This is now handled by update_cll_filter_counts_from_data
    // which is called after data is loaded
    if (_cll_summary_data) {
        update_cll_filter_counts_from_data();
    }
}

function add_cll_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), function() {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { 
                if (f[0] === 'Compliance Liability Ledger') filters[f[1]] = f[3]; 
            });
        } catch (e) {
            console.warn('Could not get filters for export:', e);
        }
        
        const url = '/api/method/ecclesia.ecclesia.doctype.compliance_liability_ledger.compliance_liability_ledger_list.export_cll_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}