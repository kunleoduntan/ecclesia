// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.listview_settings['Fixed Asset'] = {
    // ============================================
    // LIST VIEW CONFIGURATION
    // ============================================
    
    add_fields: [
        "asset_status",
        "asset_category",
        "gross_purchase_amount",
        "current_net_book_value",
        "current_accumulated_depreciation",
        "salvage_value",
        "depreciable_amount",
        "calculate_depreciation",
        "depreciation_method",
        "depreciation_frequency",
        "depreciation_percentage_complete",
        "total_number_of_depreciations",
        "useful_life_months",
        "purchase_date",
        "available_for_use_date",
        "depreciation_start_date",
        "next_depreciation_date",
        "warranty_expiry_date",
        "insurance_expiry_date",
        "company",
        "department",
        "current_location",
        "custodian",
        "asset_quantity",
        "is_existing_asset",
        "is_depreciable_asset",
        "docstatus"
    ],
    
    hide_name_column: false,
    
    filters: [
        ["docstatus", "!=", 2]
    ],
    
    // ============================================
    // STATUS INDICATORS
    // ============================================
    
    get_indicator: function(doc) {
        if (doc.docstatus === 0) {
            return ["Draft", "gray", "docstatus,=,0"];
        }
        if (doc.docstatus === 2) {
            return ["Cancelled", "darkgrey", "docstatus,=,2"];
        }
        if (doc.asset_status === "Active") {
            return ["Active", "green", "asset_status,=,Active"];
        }
        if (doc.asset_status === "Under Maintenance") {
            return ["Under Maintenance", "orange", "asset_status,=,Under Maintenance"];
        }
        if (doc.asset_status === "Fully Depreciated") {
            return ["Fully Depreciated", "blue", "asset_status,=,Fully Depreciated"];
        }
        if (doc.asset_status === "Disposed") {
            return ["Disposed", "red", "asset_status,=,Disposed"];
        }
        if (doc.asset_status === "Scrapped") {
            return ["Scrapped", "darkgrey", "asset_status,=,Scrapped"];
        }
        if (doc.asset_status === "Transferred") {
            return ["Transferred", "purple", "asset_status,=,Transferred"];
        }
        return ["Active", "green"];
    },
    
    // ============================================
    // LIST VIEW FORMATTERS
    // ============================================
    
    formatters: {
        asset_status: function(value, df, doc) {
            if (value) {
                var status_colors = {
                    'Active': '#059669',
                    'Under Maintenance': '#f59e0b',
                    'Disposed': '#dc2626',
                    'Fully Depreciated': '#3b82f6',
                    'Scrapped': '#6b7280',
                    'Transferred': '#8b5cf6',
                    'Draft': '#6b7280'
                };
                var status_icons = {
                    'Active': '✅',
                    'Under Maintenance': '🔧',
                    'Disposed': '🗑️',
                    'Fully Depreciated': '📉',
                    'Scrapped': '♻️',
                    'Transferred': '📦',
                    'Draft': '📝'
                };
                var color = status_colors[value] || '#64748b';
                var icon = status_icons[value] || '📄';
                return '<span style="display:inline-block;padding:3px 10px;border-radius:12px;' +
                    'background-color:' + color + ';color:white;font-size:10px;font-weight:600;">' +
                    icon + ' ' + value + '</span>';
            }
            return value;
        },
        
        asset_category: function(value, df, doc) {
            if (value) {
                return '<span style="font-weight:500;color:#2c3e50;font-size:12px;">' +
                    '<i class="fa fa-tag" style="color:#667eea;margin-right:6px;"></i>' + value + '</span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        gross_purchase_amount: function(value, df, doc) {
            if (value) {
                var formatted = format_currency_fa(value);
                return '<span style="font-weight:600;color:#1e293b;font-size:13px;">' +
                    '<i class="fa fa-money" style="color:#f59e0b;margin-right:4px;"></i>' +
                    formatted + '</span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        current_net_book_value: function(value, df, doc) {
            if (value) {
                var formatted = format_currency_fa(value);
                var ratio = doc.gross_purchase_amount > 0 ? (value / doc.gross_purchase_amount * 100) : 0;
                var color = ratio < 20 ? '#dc2626' : (ratio < 50 ? '#f59e0b' : '#059669');
                return '<span style="font-weight:600;color:' + color + ';font-size:12px;">' +
                    formatted + ' <span style="font-size:9px;">(' + ratio.toFixed(0) + '%)</span></span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        current_accumulated_depreciation: function(value, df, doc) {
            if (value && value > 0) {
                var formatted = format_currency_fa(value);
                return '<span style="font-weight:600;color:#dc2626;font-size:12px;">' +
                    formatted + '</span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        depreciation_percentage_complete: function(value, df, doc) {
            if (value) {
                var pct = flt_fa(value, 1);
                var color = pct >= 90 ? '#dc3545' : pct >= 50 ? '#fd7e14' : '#28a745';
                var icon = pct >= 100 ? '✅' : pct >= 90 ? '🔴' : pct >= 50 ? '🟡' : '🟢';
                return '<span style="font-weight:700;color:' + color + ';font-size:12px;">' +
                    icon + ' ' + pct + '%</span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        depreciation_method: function(value, df, doc) {
            if (value) {
                var method_colors = {
                    'Straight Line': '#059669',
                    'Written Down Value': '#f59e0b',
                    'Double Declining Balance': '#dc2626',
                    'Sum of Years Digits': '#8b5cf6'
                };
                var color = method_colors[value] || '#6b7280';
                return '<span style="font-size:11px;color:' + color + ';font-weight:600;">' +
                    '<i class="fa fa-chart-line" style="margin-right:4px;"></i>' + value + '</span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        useful_life_months: function(value, df, doc) {
            if (value) {
                var years = (value / 12).toFixed(1);
                return '<span style="font-size:11px;color:#475569;">' +
                    value + ' mo <span style="font-size:9px;color:#94a3b8;">(' + years + ' yr)</span></span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        purchase_date: function(value, df, doc) {
            if (value) {
                var today = frappe.datetime.get_today();
                var diff = frappe.datetime.get_diff(today, value);
                var years = (diff / 365).toFixed(1);
                var formatted = frappe.datetime.str_to_user(value);
                return '<span style="color:#64748b;font-size:11px;">' +
                    formatted + ' <span style="font-size:9px;color:#94a3b8;">(' + years + ' yr)</span></span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        current_location: function(value, df, doc) {
            if (value) {
                return '<span style="font-size:11px;color:#475569;">' +
                    '<i class="fa fa-map-marker" style="color:#dc2626;margin-right:4px;"></i>' + value + '</span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        custodian: function(value, df, doc) {
            if (value) {
                return '<span style="color:#475569;font-size:11px;">' +
                    '<i class="fa fa-user-circle" style="margin-right:4px;color:#667eea;"></i>' +
                    value + '</span>';
            }
            return '<span style="color:#94a3b8;">—</span>';
        },
        
        warranty_expiry_date: function(value, df, doc) {
            if (value) {
                var today = frappe.datetime.get_today();
                var diff = frappe.datetime.get_diff(value, today);
                var formatted = frappe.datetime.str_to_user(value);
                
                if (diff < 0) {
                    return '<span style="color:#dc2626;font-weight:600;font-size:11px;">' +
                        '<i class="fa fa-exclamation-triangle" style="margin-right:4px;"></i>' +
                        formatted + ' <span style="font-size:9px;">(Expired)</span></span>';
                } else if (diff <= 30) {
                    return '<span style="color:#d97706;font-weight:600;font-size:11px;">' +
                        '<i class="fa fa-bell" style="margin-right:4px;"></i>' +
                        formatted + ' <span style="font-size:9px;">(' + diff + 'd left)</span></span>';
                } else {
                    return '<span style="color:#64748b;font-size:11px;">' + formatted + '</span>';
                }
            }
            return '<span style="color:#94a3b8;">—</span>';
        }
    },
    
    // ============================================
    // ON LOAD
    // ============================================
    
    onload: function(listview) {
        setTimeout(function() {
            add_fa_styles();
            add_fa_summary_cards(listview);
            add_fa_quick_filters(listview);
            add_fa_depreciation_chart(listview);
        }, 300);
        
        add_fa_bulk_actions(listview);
        
        listview.page.wrapper.on('list-view-updated', function() {
            update_fa_summary_cards(listview);
            update_fa_filter_counts();
            update_fa_depreciation_chart(listview);
        });
    },
    
    primary_action: function() {
        frappe.new_doc("Fixed Asset");
    },
    
    colwidths: {
        "name": 140,
        "asset_status": 120,
        "asset_category": 100,
        "gross_purchase_amount": 130,
        "current_net_book_value": 130,
        "current_accumulated_depreciation": 130,
        "depreciation_percentage_complete": 80,
        "depreciation_method": 100,
        "useful_life_months": 80,
        "purchase_date": 100,
        "current_location": 120,
        "custodian": 100
    }
};

// ============================================
// ENHANCED STYLING
// ============================================

function add_fa_styles() {
    if ($('#fa-list-styles').length) return;
    
    var styles = '<style id="fa-list-styles">' +
        '.list-row{transition:all 0.2s;border-left:3px solid transparent;}' +
        '.list-row:nth-child(odd){background:linear-gradient(90deg,#ffffff,#f8fafc)!important;}' +
        '.list-row:nth-child(even){background:linear-gradient(90deg,#f8fafc,#f1f5f9)!important;}' +
        '.list-row:hover{background:linear-gradient(90deg,#eff6ff,#dbeafe)!important;border-left-color:#3b82f6!important;box-shadow:0 2px 12px rgba(59,130,246,0.12);transform:translateX(3px);}' +
        '.list-headers{background:linear-gradient(135deg,#667eea,#764ba2)!important;color:white!important;font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:0.8px;padding:12px 15px!important;}' +
        
        '/* Summary Cards */' +
        '.fa-summary-wrapper{padding:15px;background:#f8fafc;}' +
        '.fa-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;padding:15px;background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04);margin:15px 0;}' +
        '.fa-summary-card{padding:16px;border-radius:10px;text-align:center;transition:all 0.3s;background:white;border:2px solid transparent;}' +
        '.fa-summary-card:hover{transform:translateY(-4px) scale(1.02);box-shadow:0 8px 24px rgba(0,0,0,0.12);}' +
        '.fa-summary-card::before{content:"";position:absolute;top:0;left:0;right:0;height:3px;}' +
        
        '.fa-summary-card.total{background:linear-gradient(135deg,#f5f3ff,#ede9fe);border-color:#7c3aed;}' +
        '.fa-summary-card.active{background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-color:#10b981;}' +
        '.fa-summary-card.depreciation{background:linear-gradient(135deg,#fef2f2,#fee2e2);border-color:#ef4444;}' +
        '.fa-summary-card.value{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#3b82f6;}' +
        '.fa-summary-card.maintenance{background:linear-gradient(135deg,#fff7ed,#ffedd5);border-color:#f97316;}' +
        
        '.fa-card-value{font-size:18px;font-weight:700;margin:8px 0 4px 0;color:#1e293b;}' +
        '.fa-card-label{font-size:10px;text-transform:uppercase;letter-spacing:0.8px;color:#64748b;font-weight:600;}' +
        '.fa-card-sub{font-size:11px;color:#94a3b8;margin-top:4px;}' +
        
        '/* Quick Filters */' +
        '.fa-filters-wrapper{padding:0 15px 15px 15px;background:#f8fafc;}' +
        '.fa-filters{display:flex;gap:8px;padding:12px 15px;background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04);flex-wrap:wrap;align-items:center;}' +
        '.fa-filter-chip{padding:6px 14px;border-radius:20px;border:2px solid #e2e8f0;background:white;cursor:pointer;transition:all 0.2s;font-weight:500;font-size:12px;display:flex;align-items:center;gap:6px;color:#475569;}' +
        '.fa-filter-chip:hover{border-color:#667eea;background:#f5f3ff;transform:translateY(-2px);box-shadow:0 4px 8px rgba(102,126,234,0.15);}' +
        '.fa-filter-chip.active{background:linear-gradient(135deg,#667eea,#764ba2);color:white;border-color:#667eea;box-shadow:0 4px 12px rgba(102,126,234,0.3);}' +
        '.fa-filter-chip .count{display:inline-block;padding:2px 6px;background:rgba(255,255,255,0.25);border-radius:10px;font-size:10px;font-weight:700;min-width:20px;text-align:center;}' +
        '.fa-filter-chip.active .count{background:rgba(255,255,255,0.3);}' +
        
        '/* Depreciation Chart */' +
        '.fa-chart-wrapper{padding:0 15px 15px 15px;background:#f8fafc;}' +
        '.fa-chart{display:flex;gap:4px;padding:12px 15px;background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04);align-items:center;}' +
        '.fa-chart-bar{flex:1;height:8px;border-radius:4px;transition:all 0.2s;}' +
        '.fa-chart-bar:hover{transform:scaleY(2);}' +
        '.fa-chart-label{font-size:9px;color:#64748b;text-align:center;}' +
        '.fa-chart-count{font-size:9px;color:#1e293b;font-weight:600;text-align:center;}' +
        
        '@media(max-width:768px){.fa-summary{grid-template-columns:repeat(2,1fr);}}' +
        '@media(max-width:480px){.fa-summary{grid-template-columns:1fr;}}' +
        '</style>';
    
    $('head').append(styles);
}

// ============================================
// SUMMARY CARDS
// ============================================

function add_fa_summary_cards(listview) {
    $('.fa-summary-wrapper').remove();
    
    var summary_html = '<div class="fa-summary-wrapper"><div class="fa-summary">' +
        '<div class="fa-summary-card total"><div class="fa-card-label">📦 Total Assets</div><div class="fa-card-value" id="fa-total-count">--</div><div class="fa-card-sub" id="fa-total-sub">--</div></div>' +
        '<div class="fa-summary-card active"><div class="fa-card-label">✅ Active Assets</div><div class="fa-card-value" id="fa-active-count">--</div><div class="fa-card-sub" id="fa-active-sub">--</div></div>' +
        '<div class="fa-summary-card value"><div class="fa-card-label">💰 Total Value</div><div class="fa-card-value" id="fa-total-value">--</div><div class="fa-card-sub" id="fa-value-sub">--</div></div>' +
        '<div class="fa-summary-card depreciation"><div class="fa-card-label">📉 Total Depreciation</div><div class="fa-card-value" id="fa-total-dep">--</div><div class="fa-card-sub" id="fa-dep-sub">--</div></div>' +
        '<div class="fa-summary-card maintenance"><div class="fa-card-label">🔧 Under Maintenance</div><div class="fa-card-value" id="fa-maintenance-count">--</div><div class="fa-card-sub" id="fa-maintenance-sub">--</div></div>' +
        '</div></div>';
    
    var pageContent = listview.page.wrapper.find('.page-content');
    if (pageContent.length) {
        pageContent.prepend(summary_html);
    }
    
    update_fa_summary_cards(listview);
}

function update_fa_summary_cards(listview) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Fixed Asset',
            fields: ['name', 'asset_status', 'gross_purchase_amount', 'current_net_book_value', 'current_accumulated_depreciation'],
            filters: [['docstatus', '!=', 2]],
            limit_page_length: 0
        },
        callback: function(r) {
            if (r.message) {
                var data = r.message;
                var total = data.length;
                var active = data.filter(function(d) { return d.asset_status === 'Active'; }).length;
                var maintenance = data.filter(function(d) { return d.asset_status === 'Under Maintenance'; }).length;
                var totalValue = data.reduce(function(s, d) { return s + flt_fa(d.gross_purchase_amount); }, 0);
                var totalDep = data.reduce(function(s, d) { return s + flt_fa(d.current_accumulated_depreciation); }, 0);
                var totalBook = data.reduce(function(s, d) { return s + flt_fa(d.current_net_book_value); }, 0);
                
                $('#fa-total-count').text(total);
                $('#fa-total-sub').text(data.filter(function(d) { return d.asset_status === 'Fully Depreciated'; }).length + ' fully depreciated');
                
                $('#fa-active-count').text(active);
                $('#fa-active-sub').text(((active / total) * 100).toFixed(1) + '% of total');
                
                $('#fa-total-value').text(format_currency_compact_fa(totalValue));
                $('#fa-value-sub').text(format_currency_compact_fa(totalBook) + ' book value');
                
                $('#fa-total-dep').text(format_currency_compact_fa(totalDep));
                $('#fa-dep-sub').text('Accumulated');
                
                $('#fa-maintenance-count').text(maintenance);
                $('#fa-maintenance-sub').text('Need attention');
            }
        }
    });
}

function format_currency_compact_fa(amount) {
    if (!amount) return '₦0';
    if (amount >= 1000000000) return '₦' + (amount / 1000000000).toFixed(1) + 'B';
    if (amount >= 1000000) return '₦' + (amount / 1000000).toFixed(1) + 'M';
    if (amount >= 1000) return '₦' + (amount / 1000).toFixed(1) + 'K';
    return '₦' + amount.toFixed(0);
}

// ============================================
// DEPRECIATION DISTRIBUTION CHART
// ============================================

function add_fa_depreciation_chart(listview) {
    $('.fa-chart-wrapper').remove();
    
    var chart_html = '<div class="fa-chart-wrapper"><div class="fa-chart">' +
        '<div style="font-weight:600;font-size:11px;color:#64748b;margin-right:10px;">📊 Depreciation:</div>' +
        '<div style="text-align:center;"><div class="fa-chart-bar" id="fa-chart-0-25" style="background:#22c55e;" title="0-25%"></div><div class="fa-chart-label">0-25%</div><div class="fa-chart-count" id="fa-count-0-25">0</div></div>' +
        '<div style="text-align:center;"><div class="fa-chart-bar" id="fa-chart-26-50" style="background:#f59e0b;" title="26-50%"></div><div class="fa-chart-label">26-50%</div><div class="fa-chart-count" id="fa-count-26-50">0</div></div>' +
        '<div style="text-align:center;"><div class="fa-chart-bar" id="fa-chart-51-75" style="background:#f97316;" title="51-75%"></div><div class="fa-chart-label">51-75%</div><div class="fa-chart-count" id="fa-count-51-75">0</div></div>' +
        '<div style="text-align:center;"><div class="fa-chart-bar" id="fa-chart-76-99" style="background:#dc2626;" title="76-99%"></div><div class="fa-chart-label">76-99%</div><div class="fa-chart-count" id="fa-count-76-99">0</div></div>' +
        '<div style="text-align:center;"><div class="fa-chart-bar" id="fa-chart-100" style="background:#3b82f6;" title="100%"></div><div class="fa-chart-label">100%</div><div class="fa-chart-count" id="fa-count-100">0</div></div>' +
        '</div></div>';
    
    var summaryWrapper = $('.fa-summary-wrapper');
    if (summaryWrapper.length) {
        summaryWrapper.after(chart_html);
    }
    
    update_fa_depreciation_chart(listview);
}

function update_fa_depreciation_chart(listview) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Fixed Asset',
            fields: ['name', 'depreciation_percentage_complete'],
            filters: [['docstatus', '!=', 2], ['calculate_depreciation', '=', 1]],
            limit_page_length: 0
        },
        callback: function(r) {
            if (r.message) {
                var buckets = { '0-25': 0, '26-50': 0, '51-75': 0, '76-99': 0, '100': 0 };
                
                for (var i = 0; i < r.message.length; i++) {
                    var pct = flt_fa(r.message[i].depreciation_percentage_complete || 0, 1);
                    if (pct <= 25) buckets['0-25']++;
                    else if (pct <= 50) buckets['26-50']++;
                    else if (pct <= 75) buckets['51-75']++;
                    else if (pct < 100) buckets['76-99']++;
                    else buckets['100']++;
                }
                
                var maxCount = Math.max(1, buckets['0-25'], buckets['26-50'], buckets['51-75'], buckets['76-99'], buckets['100']);
                
                $('#fa-chart-0-25').css('height', Math.max(4, (buckets['0-25'] / maxCount) * 40) + 'px');
                $('#fa-chart-26-50').css('height', Math.max(4, (buckets['26-50'] / maxCount) * 40) + 'px');
                $('#fa-chart-51-75').css('height', Math.max(4, (buckets['51-75'] / maxCount) * 40) + 'px');
                $('#fa-chart-76-99').css('height', Math.max(4, (buckets['76-99'] / maxCount) * 40) + 'px');
                $('#fa-chart-100').css('height', Math.max(4, (buckets['100'] / maxCount) * 40) + 'px');
                
                $('#fa-count-0-25').text(buckets['0-25']);
                $('#fa-count-26-50').text(buckets['26-50']);
                $('#fa-count-51-75').text(buckets['51-75']);
                $('#fa-count-76-99').text(buckets['76-99']);
                $('#fa-count-100').text(buckets['100']);
            }
        }
    });
}

// ============================================
// QUICK FILTERS
// ============================================

function add_fa_quick_filters(listview) {
    $('.fa-filters-wrapper').remove();
    
    var filters_html = '<div class="fa-filters-wrapper"><div class="fa-filters">' +
        '<div class="fa-filter-chip active" data-filter="all"><i class="fa fa-list"></i> All <span class="count">0</span></div>' +
        '<div class="fa-filter-chip" data-filter="active"><i class="fa fa-check-circle"></i> Active <span class="count">0</span></div>' +
        '<div class="fa-filter-chip" data-filter="maintenance"><i class="fa fa-wrench"></i> Maintenance <span class="count">0</span></div>' +
        '<div class="fa-filter-chip" data-filter="disposed"><i class="fa fa-trash"></i> Disposed <span class="count">0</span></div>' +
        '<div class="fa-filter-chip" data-filter="depreciable"><i class="fa fa-chart-line"></i> Depreciable <span class="count">0</span></div>' +
        '<div class="fa-filter-chip" data-filter="fully-depreciated"><i class="fa fa-check-double"></i> Fully Depreciated <span class="count">0</span></div>' +
        '<div class="fa-filter-chip" data-filter="warranty-expiring"><i class="fa fa-clock-o"></i> Warranty Expiring <span class="count">0</span></div>' +
        '</div></div>';
    
    var pageContent = listview.page.wrapper.find('.page-content');
    var chartWrapper = pageContent.find('.fa-chart-wrapper');
    if (chartWrapper.length) {
        chartWrapper.after(filters_html);
    } else {
        var summaryWrapper = pageContent.find('.fa-summary-wrapper');
        if (summaryWrapper.length) {
            summaryWrapper.after(filters_html);
        } else {
            pageContent.prepend(filters_html);
        }
    }
    
    update_fa_filter_counts();
    
    $(document).off('click', '.fa-filter-chip').on('click', '.fa-filter-chip', function() {
        var filter = $(this).data('filter');
        $('.fa-filter-chip').removeClass('active');
        $(this).addClass('active');
        apply_fa_quick_filter(listview, filter);
    });
}

function update_fa_filter_counts() {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Fixed Asset',
            fields: ['name', 'asset_status', 'calculate_depreciation', 'depreciation_percentage_complete', 'warranty_expiry_date'],
            filters: [['docstatus', '!=', 2]],
            limit_page_length: 0
        },
        callback: function(r) {
            if (r.message) {
                var counts = { all: 0, active: 0, maintenance: 0, disposed: 0, depreciable: 0, 'fully-depreciated': 0, 'warranty-expiring': 0 };
                var today = frappe.datetime.get_today();
                
                for (var i = 0; i < r.message.length; i++) {
                    var d = r.message[i];
                    counts.all++;
                    if (d.asset_status === 'Active') counts.active++;
                    if (d.asset_status === 'Under Maintenance') counts.maintenance++;
                    if (d.asset_status === 'Disposed') counts.disposed++;
                    if (d.calculate_depreciation) counts.depreciable++;
                    if (d.depreciation_percentage_complete >= 100) counts['fully-depreciated']++;
                    if (d.warranty_expiry_date && frappe.datetime.get_diff(d.warranty_expiry_date, today) <= 30 && frappe.datetime.get_diff(d.warranty_expiry_date, today) >= 0) {
                        counts['warranty-expiring']++;
                    }
                }
                
                $('.fa-filter-chip[data-filter="all"] .count').text(counts.all);
                $('.fa-filter-chip[data-filter="active"] .count').text(counts.active);
                $('.fa-filter-chip[data-filter="maintenance"] .count').text(counts.maintenance);
                $('.fa-filter-chip[data-filter="disposed"] .count').text(counts.disposed);
                $('.fa-filter-chip[data-filter="depreciable"] .count').text(counts.depreciable);
                $('.fa-filter-chip[data-filter="fully-depreciated"] .count').text(counts['fully-depreciated']);
                $('.fa-filter-chip[data-filter="warranty-expiring"] .count').text(counts['warranty-expiring']);
            }
        }
    });
}

function apply_fa_quick_filter(listview, filter) {
    listview.filter_area.clear();
    
    switch(filter) {
        case 'active':
            listview.filter_area.add([['Fixed Asset', 'asset_status', '=', 'Active']]);
            break;
        case 'maintenance':
            listview.filter_area.add([['Fixed Asset', 'asset_status', '=', 'Under Maintenance']]);
            break;
        case 'disposed':
            listview.filter_area.add([['Fixed Asset', 'asset_status', '=', 'Disposed']]);
            break;
        case 'depreciable':
            listview.filter_area.add([['Fixed Asset', 'calculate_depreciation', '=', 1]]);
            break;
        case 'fully-depreciated':
            listview.filter_area.add([['Fixed Asset', 'depreciation_percentage_complete', '>=', 100]]);
            break;
        case 'warranty-expiring':
            var today = frappe.datetime.get_today();
            var thirtyDays = frappe.datetime.add_days(today, 30);
            listview.filter_area.add([
                ['Fixed Asset', 'warranty_expiry_date', 'between', [today, thirtyDays]]
            ]);
            break;
        case 'all':
        default:
            break;
    }
    
    listview.refresh();
}

// ============================================
// BULK ACTIONS
// ============================================

function add_fa_bulk_actions(listview) {
    listview.page.add_action_item(__('📅 Post Catch-up Depreciation'), function() {
        var selected = listview.get_checked_items();
        if (selected.length === 0) {
            frappe.msgprint(__('Please select at least one asset'));
            return;
        }
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.bulk_post_catchup_depreciation',
            args: {
                assets: selected.map(function(s) { return s.name; }),
                up_to_date: frappe.datetime.get_today(),
                post_as: 'individual'
            },
            freeze: true,
            freeze_message: __('⏳ Posting...'),
            callback: function(r) {
                if (r.message && r.message.success) {
                    listview.refresh();
                    frappe.show_alert({ message: __('✅ Posted successfully'), indicator: 'green' }, 5);
                }
            }
        });
    });
    
    listview.page.add_action_item(__('🔄 Generate QR Codes'), function() {
        var selected = listview.get_checked_items();
        if (selected.length === 0) {
            frappe.msgprint(__('Please select at least one asset'));
            return;
        }
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.bulk_generate_qr_codes',
            args: { assets: selected.map(function(s) { return s.name; }) },
            freeze: true,
            freeze_message: __('🔄 Generating...'),
            callback: function(r) {
                if (r.message && r.message.success) {
                    listview.refresh();
                    frappe.show_alert({ message: __('✅ QR codes generated'), indicator: 'green' }, 5);
                }
            }
        });
    });
    
    listview.page.add_menu_item(__('📊 Export Asset Report'), function() {
        window.open('/api/method/ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.export_asset_report', '_blank');
    });
}

// ============================================
// HELPERS
// ============================================

function format_currency_fa(value) {
    return frappe.format(value || 0, { fieldtype: 'Currency' });
}

function flt_fa(value, precision) {
    var num = parseFloat(value) || 0;
    if (precision === undefined) return num;
    return parseFloat(num.toFixed(precision));
}

console.log('✅ Fixed Asset List View Loaded with Powerful Dashboard');