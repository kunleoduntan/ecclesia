// Copyright (c) 2026, Value Impacts Consulting and contributors
// For license information, please see license.txt

// =============================================================================
//  BIOMETRIC DEVICE — List View Script
//  With Beautiful Dashboard, Summary Cards & Export Options
// =============================================================================

frappe.listview_settings['Biometric Device'] = {

    // ── Fields to fetch for formatting ────────────────────────────────────────
    add_fields: [
        'device_name', 'device_brand', 'protocol', 'branch',
        'ip_address', 'port', 'device_status', 'enabled',
        'last_sync', 'last_heartbeat', 'sync_mode',
        'username', 'use_https'
    ],

    hide_name_column: false,

    filters: [],

    // ── Status indicator ──────────────────────────────────────────────────────
    get_indicator: function(doc) {
        if (doc.device_status === 'Online' && doc.enabled) {
            return ['Online', 'green', 'device_status,=,Online'];
        } else if (doc.device_status === 'Offline') {
            return ['Offline', 'red', 'device_status,=,Offline'];
        } else if (doc.enabled) {
            return ['Enabled', 'blue', 'enabled,=,1'];
        } else {
            return ['Disabled', 'grey', 'enabled,=,0'];
        }
    },

    // ── Column formatters ─────────────────────────────────────────────────────
    formatters: {
        device_brand: function(v) {
            if (!v) return '';
            var icons = {
                'ZKTeco': '🔐',
                'Hikvision': '📹',
                'Dahua': '🎥',
                'Suprema': '🛡️',
                'Anviz': '📱',
                'eSSL': '🔑',
                'TAMS': '⏱️',
                'Virdi': '👁️',
                'Realand': '🏢',
                'Other': '⚙️'
            };
            var colors = {
                'ZKTeco': '#2563eb',
                'Hikvision': '#dc2626',
                'Dahua': '#d97706',
                'Suprema': '#7c3aed',
                'Anviz': '#059669',
                'eSSL': '#0891b2',
                'TAMS': '#475569',
                'Virdi': '#9333ea',
                'Realand': '#16a34a',
                'Other': '#6b7280'
            };
            return '<span style="color:' + (colors[v] || '#475569') + ';font-weight:600;">' + (icons[v] || '') + ' ' + v + '</span>';
        },

        device_name: function(v) {
            if (!v) return '';
            return '<span style="font-weight:600;color:#1e293b;">' + v + '</span>';
        },

        branch: function(v) {
            if (!v) return '';
            return '<span style="color:#4b5563;"><i class="fa fa-building"></i> ' + v + '</span>';
        },

        ip_address: function(v, df, doc) {
            if (!v) return '';
            var protocol = doc.use_https ? 'https://' : 'http://';
            var port = doc.port ? ':' + doc.port : '';
            return '<span style="font-family:monospace;font-size:12px;color:#1e3a5f;">' + protocol + v + port + '</span>';
        },

        device_status: function(v) {
            if (!v) return '';
            var colors = {
                'Online': '#16a34a',
                'Offline': '#dc2626',
                'Unknown': '#6b7280'
            };
            var icons = {
                'Online': '●',
                'Offline': '○',
                'Unknown': '◐'
            };
            return '<span style="font-weight:600;color:' + (colors[v] || '#6b7280') + ';">' + (icons[v] || '') + ' ' + v + '</span>';
        },

        enabled: function(v) {
            if (v) {
                return '<span style="color:#16a34a;font-weight:600;"><i class="fa fa-check-circle"></i> Active</span>';
            }
            return '<span style="color:#6b7280;font-weight:600;"><i class="fa fa-circle-o"></i> Inactive</span>';
        },

        protocol: function(v) {
            if (!v) return '';
            var colors = {
                'SDK': '#3b82f6',
                'HTTP API': '#8b5cf6',
                'UDP': '#059669',
                'ISAPI / REST': '#dc2626',
                'BioStar API': '#7c3aed',
                'CloudClox API': '#d97706',
                'REST API': '#0891b2'
            };
            return '<span class="badge" style="background:' + (colors[v] || '#475569') + ';color:white;padding:2px 8px;border-radius:12px;font-size:10px;">' + v + '</span>';
        },

        last_sync: function(v) {
            if (!v) return '';
            var diff = frappe.datetime.get_diff(frappe.datetime.now_datetime(), v);
            var color = diff < 60 ? '#16a34a' : diff < 300 ? '#d97706' : '#dc2626';
            return '<span style="color:' + color + ';font-size:12px;">' + frappe.datetime.str_to_user(v) + '</span>';
        },

        sync_mode: function(v) {
            if (!v) return '';
            var color = v === 'Push (Real-time)' ? '#059669' : '#2563eb';
            var icon = v === 'Push (Real-time)' ? '📡' : '⏰';
            return '<span style="color:' + color + ';font-size:12px;">' + icon + ' ' + v + '</span>';
        }
    },

    // ── Column widths ─────────────────────────────────────────────────────────
    colwidths: {
        'device_name': 180,
        'device_brand': 130,
        'ip_address': 200,
        'device_status': 100,
        'branch': 140,
        'protocol': 130,
        'last_sync': 150
    },

    // ── On page load ──────────────────────────────────────────────────────────
    onload: function(listview) {
        _bd_add_styles();
        setTimeout(function() {
            _bd_add_summary_cards(listview);
            _bd_add_quick_filters(listview);
        }, 500);
        _bd_add_export_options(listview);
        listview.page.wrapper.on('list-view-updated', function() {
            _bd_update_summary_cards(listview);
            _bd_update_filter_counts();
        });
    },

    // ── Primary action button ─────────────────────────────────────────────────
    primary_action: function() {
        frappe.new_doc('Biometric Device');
    },

    // ── Row-level button ──────────────────────────────────────────────────────
    button: {
        show: function(doc) {
            return doc.name;
        },
        get_label: function() {
            return __('⚡ Actions');
        },
        get_description: function() {
            return __('Quick Actions');
        },
        action: function(doc) {
            _bd_show_row_actions(doc);
        }
    }
};


// =============================================================================
//  STYLES
// =============================================================================

function _bd_add_styles() {
    if ($('#bd-list-styles').length) return;

    $('head').append(`
        <style id="bd-list-styles">
            /* Row styling */
            .list-row {
                transition: all 0.2s ease;
                border-left: 3px solid transparent;
            }
            .list-row:nth-child(odd) {
                background: linear-gradient(90deg, #ffffff, #fafafa) !important;
            }
            .list-row:nth-child(even) {
                background: linear-gradient(90deg, #fafafa, #f5f5f5) !important;
            }
            .list-row:hover {
                background: linear-gradient(90deg, #eff6ff, #dbeafe) !important;
                border-left-color: #2563eb !important;
                transform: translateX(3px);
            }
            .list-row[data-status="Online"] {
                border-left-color: #16a34a;
            }
            .list-row[data-status="Offline"] {
                background: linear-gradient(90deg, #fef2f2, #fee2e2) !important;
                border-left-color: #dc2626 !important;
            }

            /* Header styling */
            .list-headers {
                background: linear-gradient(135deg, #1e3a5f, #2563eb) !important;
                color: #ffffff !important;
                font-weight: 600;
                text-transform: uppercase;
                font-size: 11px;
                letter-spacing: 0.8px;
                padding: 12px 15px !important;
            }

            /* Summary cards container */
            .bd-summary-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 12px;
                padding: 15px;
                background: #ffffff;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                margin: 15px;
            }

            /* Summary card styling */
            .bd-summary-card {
                padding: 16px;
                border-radius: 10px;
                text-align: center;
                transition: all 0.3s ease;
                border: 2px solid transparent;
                cursor: pointer;
            }
            .bd-summary-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
            }
            .bd-summary-card.total {
                background: linear-gradient(135deg, #eff6ff, #dbeafe);
                border-color: #3b82f6;
            }
            .bd-summary-card.online {
                background: linear-gradient(135deg, #ecfdf5, #d1fae5);
                border-color: #10b981;
            }
            .bd-summary-card.offline {
                background: linear-gradient(135deg, #fef2f2, #fee2e2);
                border-color: #ef4444;
            }
            .bd-summary-card.zkteco {
                background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
                border-color: #6366f1;
            }
            .bd-summary-card.hikvision {
                background: linear-gradient(135deg, #fee2e2, #fecaca);
                border-color: #dc2626;
            }
            .bd-summary-card-value {
                font-size: 20px;
                font-weight: 700;
                margin: 8px 0 4px;
                color: #1e293b;
            }
            .bd-summary-card-label {
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                color: #64748b;
                font-weight: 600;
            }
            .bd-summary-card-count {
                font-size: 11px;
                color: #94a3b8;
                margin-top: 4px;
            }

            /* Quick filters */
            .bd-filters-container {
                display: flex;
                gap: 8px;
                padding: 12px 15px;
                background: #ffffff;
                border-radius: 12px;
                margin: 0 15px 12px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                flex-wrap: wrap;
            }
            .bd-filter-chip {
                padding: 6px 14px;
                border-radius: 20px;
                border: 2px solid #e2e8f0;
                background: #ffffff;
                cursor: pointer;
                transition: all 0.2s ease;
                font-weight: 500;
                font-size: 12px;
                display: flex;
                align-items: center;
                gap: 6px;
                color: #475569;
            }
            .bd-filter-chip:hover {
                border-color: #2563eb;
                background: #eff6ff;
                transform: translateY(-2px);
            }
            .bd-filter-chip.active {
                background: linear-gradient(135deg, #1e3a5f, #2563eb);
                color: #ffffff;
                border-color: #2563eb;
            }
            .bd-filter-chip .count {
                display: inline-block;
                padding: 2px 6px;
                background: rgba(0, 0, 0, 0.08);
                border-radius: 10px;
                font-size: 10px;
                font-weight: 700;
                min-width: 20px;
                text-align: center;
            }
            .bd-filter-chip.active .count {
                background: rgba(255, 255, 255, 0.25);
            }

            /* Action menu items */
            .bd-action-item {
                padding: 12px 16px;
                cursor: pointer;
                border-radius: 6px;
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 2px;
                transition: background 0.2s ease;
            }
            .bd-action-item:hover {
                background: #eff6ff;
            }

            /* Responsive */
            @media (max-width: 768px) {
                .bd-summary-container {
                    grid-template-columns: repeat(2, 1fr);
                    gap: 8px;
                    padding: 10px;
                }
                .bd-summary-card {
                    padding: 12px;
                }
                .bd-summary-card-value {
                    font-size: 16px;
                }
                .bd-filters-container {
                    overflow-x: auto;
                    flex-wrap: nowrap;
                }
            }
        </style>
    `);
}


// =============================================================================
//  SUMMARY CARDS
// =============================================================================

function _bd_add_summary_cards(listview) {
    $('.bd-summary-container').remove();

    var $pageContent = listview.page.wrapper.find('.page-content');
    if (!$pageContent.length) return;

    var html = `
        <div class="bd-summary-container">
            <div class="bd-summary-card total" data-filter="all">
                <div class="bd-summary-card-label">📊 Total Devices</div>
                <div class="bd-summary-card-value" id="bd-total-count">--</div>
                <div class="bd-summary-card-count" id="bd-total-sub">All devices</div>
            </div>
            <div class="bd-summary-card online" data-filter="online">
                <div class="bd-summary-card-label">🟢 Online</div>
                <div class="bd-summary-card-value" id="bd-online-count">--</div>
                <div class="bd-summary-card-count" id="bd-online-sub">Active devices</div>
            </div>
            <div class="bd-summary-card offline" data-filter="offline">
                <div class="bd-summary-card-label">🔴 Offline</div>
                <div class="bd-summary-card-value" id="bd-offline-count">--</div>
                <div class="bd-summary-card-count" id="bd-offline-sub">Inactive devices</div>
            </div>
            <div class="bd-summary-card zkteco" data-filter="zkteco">
                <div class="bd-summary-card-label">🔐 ZKTeco</div>
                <div class="bd-summary-card-value" id="bd-zkteco-count">--</div>
                <div class="bd-summary-card-count" id="bd-zkteco-sub">Most common brand</div>
            </div>
            <div class="bd-summary-card hikvision" data-filter="hikvision">
                <div class="bd-summary-card-label">📹 Hikvision</div>
                <div class="bd-summary-card-value" id="bd-hikvision-count">--</div>
                <div class="bd-summary-card-count" id="bd-hikvision-sub">Camera-based</div>
            </div>
        </div>
    `;

    $pageContent.prepend(html);

    $('.bd-summary-card[data-filter]').on('click', function() {
        var filter = $(this).data('filter');
        _bd_apply_quick_filter(listview, filter);
    });

    _bd_update_summary_cards(listview);
}

function _bd_update_summary_cards(listview) {
    // Use frappe.db.count directly from client side
    var summaryData = {
        total: 0,
        online: 0,
        offline: 0,
        zkteco: 0,
        hikvision: 0,
        enabled: 0
    };

    // Count total
    frappe.call({
        method: 'frappe.client.get_count',
        args: {
            doctype: 'Biometric Device'
        },
        callback: function(r) {
            summaryData.total = r.message || 0;
            updateSummaryDisplay();
        }
    });

    // Count online
    frappe.call({
        method: 'frappe.client.get_count',
        args: {
            doctype: 'Biometric Device',
            filters: { device_status: 'Online' }
        },
        callback: function(r) {
            summaryData.online = r.message || 0;
            updateSummaryDisplay();
        }
    });

    // Count offline
    frappe.call({
        method: 'frappe.client.get_count',
        args: {
            doctype: 'Biometric Device',
            filters: { device_status: 'Offline' }
        },
        callback: function(r) {
            summaryData.offline = r.message || 0;
            updateSummaryDisplay();
        }
    });

    // Count ZKTeco
    frappe.call({
        method: 'frappe.client.get_count',
        args: {
            doctype: 'Biometric Device',
            filters: { device_brand: 'ZKTeco' }
        },
        callback: function(r) {
            summaryData.zkteco = r.message || 0;
            updateSummaryDisplay();
        }
    });

    // Count Hikvision
    frappe.call({
        method: 'frappe.client.get_count',
        args: {
            doctype: 'Biometric Device',
            filters: { device_brand: 'Hikvision' }
        },
        callback: function(r) {
            summaryData.hikvision = r.message || 0;
            updateSummaryDisplay();
        }
    });

    // Count enabled
    frappe.call({
        method: 'frappe.client.get_count',
        args: {
            doctype: 'Biometric Device',
            filters: { enabled: 1 }
        },
        callback: function(r) {
            summaryData.enabled = r.message || 0;
            updateSummaryDisplay();
        }
    });

    var updateCount = 0;
    var totalCalls = 6;

    function updateSummaryDisplay() {
        updateCount++;
        if (updateCount >= totalCalls) {
            var total = summaryData.total || 0;
            var online = summaryData.online || 0;
            var offline = summaryData.offline || 0;
            var zkteco = summaryData.zkteco || 0;
            var hikvision = summaryData.hikvision || 0;
            var enabled = summaryData.enabled || 0;

            $('#bd-total-count').text(total);
            $('#bd-total-sub').text(enabled + ' enabled');

            $('#bd-online-count').text(online);
            $('#bd-online-sub').text(total > 0 ? Math.round((online / total) * 100) + '% of total' : '0%');

            $('#bd-offline-count').text(offline);
            $('#bd-offline-sub').text(total > 0 ? Math.round((offline / total) * 100) + '% of total' : '0%');

            $('#bd-zkteco-count').text(zkteco);
            $('#bd-zkteco-sub').text('ZKTeco devices');

            $('#bd-hikvision-count').text(hikvision);
            $('#bd-hikvision-sub').text('Hikvision devices');
        }
    }
}


// =============================================================================
//  QUICK FILTERS
// =============================================================================

function _bd_add_quick_filters(listview) {
    $('.bd-filters-container').remove();

    var $pageContent = listview.page.wrapper.find('.page-content');
    if (!$pageContent.length) return;

    var $summaryContainer = $pageContent.find('.bd-summary-container');

    var filters = [
        { id: 'all', icon: 'fa-list', label: 'All Devices' },
        { id: 'online', icon: 'fa-check-circle', label: 'Online' },
        { id: 'offline', icon: 'fa-exclamation-circle', label: 'Offline' },
        { id: 'enabled', icon: 'fa-play', label: 'Enabled' },
        { id: 'zkteco', icon: 'fa-lock', label: 'ZKTeco' },
        { id: 'hikvision', icon: 'fa-video-camera', label: 'Hikvision' },
        { id: 'push', icon: 'fa-bolt', label: 'Push Mode' }
    ];

    var chipsHtml = '<div class="bd-filters-container">';
    filters.forEach(function(f) {
        chipsHtml += `<div class="bd-filter-chip ${f.id === 'all' ? 'active' : ''}" data-filter="${f.id}">
            <i class="fa ${f.icon}"></i> ${f.label}
            <span class="count">0</span>
        </div>`;
    });
    chipsHtml += '</div>';

    if ($summaryContainer.length) {
        $summaryContainer.after(chipsHtml);
    } else {
        $pageContent.prepend(chipsHtml);
    }

    _bd_update_filter_counts();

    $(document).off('click.bd', '.bd-filter-chip').on('click.bd', '.bd-filter-chip', function() {
        var filter = $(this).data('filter');
        $('.bd-filter-chip').removeClass('active');
        $(this).addClass('active');
        _bd_apply_quick_filter(listview, filter);
    });
}

function _bd_update_filter_counts() {
    var counts = {
        total: 0,
        online: 0,
        offline: 0,
        enabled: 0,
        zkteco: 0,
        hikvision: 0,
        push: 0
    };
    var updateCount = 0;
    var totalCalls = 7;

    function updateFilterDisplay() {
        updateCount++;
        if (updateCount >= totalCalls) {
            $('.bd-filter-chip[data-filter="all"] .count').text(counts.total || 0);
            $('.bd-filter-chip[data-filter="online"] .count').text(counts.online || 0);
            $('.bd-filter-chip[data-filter="offline"] .count').text(counts.offline || 0);
            $('.bd-filter-chip[data-filter="enabled"] .count').text(counts.enabled || 0);
            $('.bd-filter-chip[data-filter="zkteco"] .count').text(counts.zkteco || 0);
            $('.bd-filter-chip[data-filter="hikvision"] .count').text(counts.hikvision || 0);
            $('.bd-filter-chip[data-filter="push"] .count').text(counts.push || 0);
        }
    }

    frappe.call({
        method: 'frappe.client.get_count',
        args: { doctype: 'Biometric Device' },
        callback: function(r) { counts.total = r.message || 0; updateFilterDisplay(); }
    });

    frappe.call({
        method: 'frappe.client.get_count',
        args: { doctype: 'Biometric Device', filters: { device_status: 'Online' } },
        callback: function(r) { counts.online = r.message || 0; updateFilterDisplay(); }
    });

    frappe.call({
        method: 'frappe.client.get_count',
        args: { doctype: 'Biometric Device', filters: { device_status: 'Offline' } },
        callback: function(r) { counts.offline = r.message || 0; updateFilterDisplay(); }
    });

    frappe.call({
        method: 'frappe.client.get_count',
        args: { doctype: 'Biometric Device', filters: { enabled: 1 } },
        callback: function(r) { counts.enabled = r.message || 0; updateFilterDisplay(); }
    });

    frappe.call({
        method: 'frappe.client.get_count',
        args: { doctype: 'Biometric Device', filters: { device_brand: 'ZKTeco' } },
        callback: function(r) { counts.zkteco = r.message || 0; updateFilterDisplay(); }
    });

    frappe.call({
        method: 'frappe.client.get_count',
        args: { doctype: 'Biometric Device', filters: { device_brand: 'Hikvision' } },
        callback: function(r) { counts.hikvision = r.message || 0; updateFilterDisplay(); }
    });

    frappe.call({
        method: 'frappe.client.get_count',
        args: { doctype: 'Biometric Device', filters: { sync_mode: 'Push (Real-time)' } },
        callback: function(r) { counts.push = r.message || 0; updateFilterDisplay(); }
    });
}

function _bd_apply_quick_filter(listview, filter) {
    listview.filter_area.clear();

    var dt = 'Biometric Device';
    var filters = {
        'online': [[dt, 'device_status', '=', 'Online']],
        'offline': [[dt, 'device_status', '=', 'Offline']],
        'enabled': [[dt, 'enabled', '=', 1]],
        'zkteco': [[dt, 'device_brand', '=', 'ZKTeco']],
        'hikvision': [[dt, 'device_brand', '=', 'Hikvision']],
        'push': [[dt, 'sync_mode', '=', 'Push (Real-time)']]
    };

    if (filters[filter]) {
        filters[filter].forEach(function(f) {
            listview.filter_area.add(f);
        });
    }

    listview.refresh();
}


// =============================================================================
//  EXPORT OPTIONS
// =============================================================================

function _bd_add_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel (All Devices)'), function() {
        _bd_export_to_excel('all');
    });

    listview.page.add_menu_item(__('📈 Export Online/Offline Report'), function() {
        _bd_export_to_excel('status');
    });

    listview.page.add_menu_item(__('📋 Export Device Configuration'), function() {
        _bd_export_configuration();
    });
}

function _bd_export_to_excel(type) {
    // Get all visible rows
    var data = [];
    var rows = frappe.listview_settings['Biometric Device'].get_visible_rows();
    
    if (rows && rows.length) {
        rows.forEach(function(row) {
            var doc = row.doc;
            data.push({
                'Device Name': doc.device_name || '',
                'Brand': doc.device_brand || '',
                'Protocol': doc.protocol || '',
                'Branch': doc.branch || '',
                'IP Address': doc.ip_address || '',
                'Port': doc.port || '',
                'Status': doc.device_status || '',
                'Enabled': doc.enabled ? 'Yes' : 'No',
                'Sync Mode': doc.sync_mode || '',
                'Last Sync': doc.last_sync || '',
                'Username': doc.username || ''
            });
        });
    }

    if (!data.length) {
        frappe.msgprint(__('No data to export.'));
        return;
    }

    // Use Frappe's built-in export
    frappe.call({
        method: 'frappe.core.doctype.data_export.exporter.export_data',
        args: {
            doctype: 'Biometric Device',
            export_fields: [
                {'fieldname': 'device_name', 'label': 'Device Name'},
                {'fieldname': 'device_brand', 'label': 'Brand'},
                {'fieldname': 'protocol', 'label': 'Protocol'},
                {'fieldname': 'branch', 'label': 'Branch'},
                {'fieldname': 'ip_address', 'label': 'IP Address'},
                {'fieldname': 'port', 'label': 'Port'},
                {'fieldname': 'device_status', 'label': 'Status'},
                {'fieldname': 'enabled', 'label': 'Enabled'},
                {'fieldname': 'sync_mode', 'label': 'Sync Mode'},
                {'fieldname': 'last_sync', 'label': 'Last Sync'},
                {'fieldname': 'username', 'label': 'Username'}
            ],
            file_type: 'Excel'
        },
        callback: function(r) {
            if (r.message && r.message.file_url) {
                window.open(r.message.file_url, '_blank');
                frappe.show_alert({
                    message: __('Excel report generated!'),
                    indicator: 'green'
                });
            }
        }
    });
}

function _bd_export_configuration() {
    // Get all devices
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Biometric Device',
            fields: ['device_name', 'device_brand', 'protocol', 'ip_address', 'port', 'username', 'sync_mode'],
            order_by: 'device_name asc'
        },
        callback: function(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint(__('No devices found.'));
                return;
            }

            var data = r.message;
            var html = '<h5>📋 Device Configuration Export</h5>';
            html += '<table class="table table-bordered" style="font-size:12px;">';
            html += '<thead><tr><th>Device Name</th><th>Brand</th><th>Protocol</th><th>IP Address</th><th>Port</th><th>Username</th><th>Sync Mode</th></tr></thead><tbody>';

            data.forEach(function(d) {
                html += '<tr>';
                html += '<td><strong>' + (d.device_name || '') + '</strong></td>';
                html += '<td>' + (d.device_brand || '') + '</td>';
                html += '<td>' + (d.protocol || '') + '</td>';
                html += '<td><code>' + (d.ip_address || '') + '</code></td>';
                html += '<td>' + (d.port || '') + '</td>';
                html += '<td>' + (d.username || '') + '</td>';
                html += '<td>' + (d.sync_mode || '') + '</td>';
                html += '</tr>';
            });

            html += '</tbody></table>';
            html += '<p style="margin-top:10px;font-size:11px;color:#6b7280;">Exported: ' + new Date().toLocaleString() + '</p>';

            frappe.msgprint({
                title: __('Device Configuration'),
                message: html,
                wide: true
            });
        }
    });
}


// =============================================================================
//  ROW ACTIONS
// =============================================================================

function _bd_show_row_actions(doc) {
    var actions = [
        {
            label: __('👁️ View Device'),
            icon: 'fa-eye',
            action: function() {
                frappe.set_route('Form', 'Biometric Device', doc.name);
            }
        },
        {
            label: __('📋 Duplicate'),
            icon: 'fa-copy',
            action: function() {
                frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'Biometric Device', name: doc.name },
                    callback: function(r) {
                        if (!r.message) return;
                        var newDoc = frappe.model.copy_doc(r.message);
                        newDoc.device_name = newDoc.device_name + ' (Copy)';
                        frappe.set_route('Form', 'Biometric Device', newDoc.name);
                    }
                });
            }
        },
        {
            label: __('🔗 View Branch'),
            icon: 'fa-building',
            action: function() {
                if (doc.branch) {
                    frappe.set_route('Form', 'Branch', doc.branch);
                } else {
                    frappe.msgprint(__('No branch linked to this device.'));
                }
            }
        }
    ];

    var itemsHtml = '';
    for (var i = 0; i < actions.length; i++) {
        itemsHtml += `<div class="bd-action-item" data-idx="${i}">
            <i class="fa ${actions[i].icon}" style="width: 20px;"></i>
            <span>${actions[i].label}</span>
        </div>`;
    }

    var dialog = new frappe.ui.Dialog({
        title: __('Quick Actions — ') + (doc.device_name || doc.name),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'actions_html',
            options: '<div style="padding: 4px;">' + itemsHtml + '</div>'
        }]
    });

    dialog.show();

    dialog.$wrapper.find('.bd-action-item').each(function(idx) {
        $(this).on('click', function() {
            actions[idx].action();
            dialog.hide();
        });
    });
}