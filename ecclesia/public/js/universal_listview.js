// Copyright (c) 2025, Investment Management and contributors
// For license information, please see license.txt

// ============================================================
//  🎀 UNIVERSAL LISTVIEW - Complete Production Ready Code 🎀
//  Professional, Cute, and Ridiculously Powerful
// ============================================================

(function() {
    'use strict';

    // ============================================================
    //  🎨 COLOR ENGINE - Rainbow Magic!
    // ============================================================
    
    function _ulvHash(str) {
        let h = 5381;
        for (let i = 0; i < str.length; i++) {
            h = ((h << 5) + h) + str.charCodeAt(i);
            h |= 0;
        }
        return Math.abs(h);
    }

    function _getColorFromString(str, variant = 'badge') {
        if (!str) return { bg: '#f8f9fa', text: '#6c757d', border: '#dee2e6', emoji: '📄' };
        
        const hue = _ulvHash(str) % 360;
        const sat = 65 + _ulvHash(str + 'S') % 25;
        
        if (variant === 'badge') {
            const lBg = 92 + _ulvHash(str + 'B') % 6;
            const lText = 35 + _ulvHash(str + 'T') % 12;
            const emojis = ['🌸', '⭐', '💎', '🌟', '✨', '🎀', '💝', '🎈', '🌈', '⭐', '💖', '🎨'];
            return {
                bg: `hsl(${hue},${sat}%,${lBg}%)`,
                text: `hsl(${hue},${sat}%,${lText}%)`,
                border: `hsl(${hue},${sat}%,${lText + 18}%)`,
                emoji: emojis[_ulvHash(str + 'E') % emojis.length]
            };
        } else {
            const lDark = 42 + _ulvHash(str + 'L') % 18;
            return {
                bg: `hsl(${hue},${sat}%,94%)`,
                text: `hsl(${hue},${sat}%,${lDark}%)`,
                border: `hsl(${hue},${sat}%,${lDark + 20}%)`
            };
        }
    }

    function _autoBadge(value) {
        if (!value) return '';
        const c = _getColorFromString(String(value), 'badge');
        return `<span class="ulv-badge" style="background:${c.bg};color:${c.text};border:1px solid ${c.border};">
                    <span style="margin-right:4px;">${c.emoji}</span>${value}
                </span>`;
    }

    // ============================================================
    //  🏷️ ICON ENGINE
    // ============================================================
    
    const _ICON_MAP = {
        'MAT': 'fa-car', 'MTR': 'fa-car', 'VEH': 'fa-car', 'AUTO': 'fa-car',
        'MAR': 'fa-ship', 'SHP': 'fa-ship', 'BOAT': 'fa-ship',
        'AVI': 'fa-plane', 'AIR': 'fa-plane', 'FLY': 'fa-plane',
        'FIR': 'fa-fire', 'PRP': 'fa-home', 'HOM': 'fa-home', 'BLD': 'fa-building',
        'LIF': 'fa-heart', 'HLT': 'fa-heartbeat', 'MED': 'fa-medkit',
        'ENG': 'fa-cogs', 'OIL': 'fa-tint', 'GAS': 'fa-tint', 'ENR': 'fa-bolt',
        'TRV': 'fa-suitcase', 'TRL': 'fa-suitcase', 'GLB': 'fa-globe',
        'GRP': 'fa-users', 'LIB': 'fa-balance-scale', 'LIA': 'fa-balance-scale',
        'BND': 'fa-university', 'FIN': 'fa-money', 'CSH': 'fa-credit-card',
        'INV': 'fa-file-text', 'ORD': 'fa-shopping-cart', 'SAL': 'fa-tag', 'POL': 'fa-file-contract',
        'SIN': 'fa-receipt', 'PIN': 'fa-receipt', 'PUR': 'fa-truck', 'QUO': 'fa-file-alt'
    };

    function _getIconForSeries(value) {
        if (!value) return 'fa-file-alt';
        const prefix = String(value).split(/[-_/]+/)[0].toUpperCase();
        return _ICON_MAP[prefix] || 'fa-file-alt';
    }

    // ============================================================
    //  💰 CURRENCY ENGINE
    // ============================================================
    
    const _SYMBOLS = {
        NGN: '₦', USD: '$', GBP: '£', EUR: '€', GHS: '₵',
        KES: 'KSh', ZAR: 'R', XOF: 'CFA', JPY: '¥', CNY: '¥',
        INR: '₹', BRL: 'R$', CAD: 'CA$', AUD: 'A$', CHF: 'Fr',
        AED: 'د.إ', SAR: '﷼', EGP: 'E£', MAD: 'MAD', TZS: 'TSh',
        UGX: 'USh', RWF: 'RF', XAF: 'FCFA', MWK: 'MK', ZMW: 'ZK'
    };

    function _getSymbol(code) {
        return _SYMBOLS[(code || '').toUpperCase()] || ((code || '') + ' ');
    }

    function _formatCompactCurrency(amount, currency) {
        if (!amount && amount !== 0) return _getSymbol(currency) + '—';
        const symbol = _getSymbol(currency);
        const absAmount = Math.abs(amount);
        
        if (absAmount >= 1e9) return symbol + (amount / 1e9).toFixed(1) + 'B';
        if (absAmount >= 1e6) return symbol + (amount / 1e6).toFixed(1) + 'M';
        if (absAmount >= 1e3) return symbol + (amount / 1e3).toFixed(1) + 'K';
        return symbol + amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // ============================================================
    //  🏭 MAIN UNIVERSAL LISTVIEW CLASS
    // ============================================================
    
    const UniversalListViewConfig = {
        // Global settings
        global: {
            enabled: true,
            debug: false,
            enableAnimations: true,
            enableConfetti: true,
            enableWelcomeMsg: true,
            summaryCards: true,
            quickFilters: true,
            zebraStriping: true,
            stylesInjected: false
        },
        
        // Doctype-specific configurations
        doctypes: {},
        
        // Registered doctypes from server
        registeredDoctypes: [],
        
        /**
         * Register a doctype with custom configuration
         */
        register(doctype, config) {
            if (!this.global.enabled) {
                if (this.global.debug) console.log(`[ULV] Skipped ${doctype} (disabled globally)`);
                return;
            }
            
            this.doctypes[doctype] = {
                add_fields: [],
                amount_fields: [],
                badge_fields: [],
                series_field: 'naming_series',
                date_fields: [],
                due_date_field: 'due_date',
                paid_field: 'receipt_no',
                currency_field: 'currency',
                filters: [],
                quick_filters: [],
                colwidths: {},
                summary_method: null,
                filter_method: null,
                send_method: null,
                export_base: null,
                showSummaryCards: true,
                showQuickFilters: true,
                showZebraStriping: true,
                showRowActions: true,
                showBulkActions: true,
                showExportOptions: true,
                onLoad: null,
                onRefresh: null,
                customFormatters: {},
                customIndicators: null,
                ...config,
                _registered: true,
                _registeredAt: new Date().toISOString()
            };
            
            if (this.global.debug) {
                console.log(`[ULV] ✅ Registered ${doctype}`, this.doctypes[doctype]);
            }
            
            // Apply the listview settings
            this._applyToDoctype(doctype);
        },
        
        /**
         * Register multiple doctypes at once
         */
        registerBatch(doctypesConfig) {
            Object.entries(doctypesConfig).forEach(([doctype, config]) => {
                this.register(doctype, config);
            });
        },
        
        /**
         * Apply listview settings to a doctype
         */
        _applyToDoctype(doctype) {
            const config = this.doctypes[doctype];
            if (!config) return;
            
            const applySettings = () => {
                if (window.frappe && frappe.listview_settings) {
                    this._injectListviewSettings(doctype, config);
                } else {
                    $(document).one('frappe-ready', () => {
                        this._injectListviewSettings(doctype, config);
                    });
                }
            };
            
            if (document.readyState === 'loading') {
                $(document).ready(applySettings);
            } else {
                applySettings();
            }
        },
        
        /**
         * Inject listview settings
         */
        _injectListviewSettings(doctype, config) {
            const existing = frappe.listview_settings[doctype] || {};
            
            frappe.listview_settings[doctype] = {
                ...existing,
                add_fields: config.add_fields,
                hide_name_column: false,
                filters: config.filters,
                colwidths: config.colwidths,
                formatters: this._buildFormatters(config),
                get_indicator: config.customIndicators || ((doc) => this._getIndicator(doc, config)),
                button: config.showRowActions ? {
                    show: (doc) => !!doc.name,
                    get_label: () => '✨ Actions',
                    get_description: () => 'Quick Actions ✨',
                    action: (doc) => this._showRowActions(doc, doctype, config)
                } : null,
                primary_action: () => {
                    frappe.new_doc(doctype);
                    if (this.global.enableAnimations) {
                        frappe.show_alert({ message: `✨ Creating new ${doctype}...`, indicator: 'green' }, 2);
                    }
                },
                onload: (listview) => {
                    if (existing.onload) existing.onload(listview);
                    this._enhanceListview(listview, doctype, config);
                    if (config.onLoad && typeof config.onLoad === 'function') {
                        config.onLoad(listview);
                    }
                }
            };
            
            if (this.global.debug) {
                console.log(`[ULV] 🎨 Applied settings to ${doctype}`);
            }
        },
        
        /**
         * Build formatters from config
         */
        _buildFormatters(config) {
            const formatters = {};
            
            // Series field
            if (config.series_field) {
                formatters[config.series_field] = (value) => {
                    if (!value) return value;
                    const icon = _getIconForSeries(value);
                    return `<div class="ulv-series">
                                <i class="fa ${icon} ulv-icon-accent"></i>
                                <span>${value}</span>
                            </div>`;
                };
            }
            
            // Amount fields
            config.amount_fields.forEach((field, idx) => {
                const cls = idx === 0 ? 'ulv-amount-primary' : 'ulv-amount-secondary';
                formatters[field] = (value, df, doc) => {
                    if (!value && value !== 0) return '—';
                    const formatted = format_currency(value, doc[config.currency_field]);
                    return `<div class="${cls}">
                                <span class="ulv-currency-icon">💰</span> ${formatted}
                            </div>`;
                };
            });
            
            // Badge fields
            config.badge_fields.forEach(field => {
                formatters[field] = (value) => _autoBadge(value);
            });
            
            // Date fields
            config.date_fields.forEach(field => {
                if (field === config.due_date_field) return;
                formatters[field] = (value) => {
                    if (!value) return '—';
                    return `<div class="ulv-date">📅 ${frappe.datetime.str_to_user(value)}</div>`;
                };
            });
            
            // Due date field
            if (config.due_date_field) {
                formatters[config.due_date_field] = (value, df, doc) => {
                    return this._formatDueDate(value, doc, config);
                };
            }
            
            // Custom formatters
            if (config.customFormatters) {
                Object.assign(formatters, config.customFormatters);
            }
            
            return formatters;
        },
        
        /**
         * Format due date with urgency indicators
         */
        _formatDueDate(value, doc, config) {
            if (!value) return '—';
            const today = frappe.datetime.get_today();
            const diff = frappe.datetime.get_diff(value, today);
            const label = frappe.datetime.str_to_user(value);
            const isPaid = !!(doc[config.paid_field] && doc.docstatus === 1);
            const isCancelled = doc.docstatus === 2;
            
            if (isCancelled) return `<div class="ulv-date">📅 ${label}</div>`;
            
            if (diff < 0 && !isPaid) {
                const urgency = Math.abs(diff);
                const faces = ['😰', '😱', '💀', '🚨', '⏰'];
                const face = urgency > 30 ? faces[2] : urgency > 14 ? faces[1] : faces[0];
                return `<div class="ulv-date ulv-date-overdue">
                            <span>${face}</span> ${label}
                            <span class="ulv-day-tag">${Math.abs(diff)}d overdue</span>
                        </div>`;
            }
            
            if (diff <= 7 && diff >= 0 && !isPaid) {
                const faces = ['😊', '😌', '🤗', '💪'];
                return `<div class="ulv-date ulv-date-soon">
                            <span>${faces[diff] || '⏰'}</span> ${label}
                            <span class="ulv-day-tag">${diff}d left</span>
                        </div>`;
            }
            
            return `<div class="ulv-date">📅 ${label}</div>`;
        },
        
        /**
         * Get indicator based on document status
         */
        _getIndicator(doc, config) {
            const isPaid = !!(doc[config.paid_field] && doc.docstatus === 1);
            const isOverdue = (!isPaid && doc[config.due_date_field] && doc.docstatus === 1 && 
                               frappe.datetime.get_diff(frappe.datetime.get_today(), doc[config.due_date_field]) > 0);
            
            if (isPaid) return ['green', '✅ Paid', `${config.paid_field},!=,`];
            if (isOverdue) return ['red', '⚠️ Overdue', `${config.due_date_field},<,Today|${config.paid_field},is,null`];
            if (doc.docstatus === 0) return ['orange', '📝 Draft', 'docstatus,=,0'];
            if (doc.docstatus === 1) return ['blue', '💙 Active', `${config.paid_field},is,null|docstatus,=,1`];
            if (doc.docstatus === 2) return ['gray', '🗑️ Cancelled', 'docstatus,=,2'];
            return ['gray', '❓ Unknown'];
        },
        
        /**
         * Enhance listview with additional UI
         */
        _enhanceListview(listview, doctype, config) {
            this._injectStyles();
            
            if (config.showSummaryCards && config.summary_method) {
                this._buildSummaryCards(listview, config);
            }
            
            if (config.showQuickFilters) {
                this._buildQuickFilters(listview, doctype, config);
            }
            
            if (config.showBulkActions && config.send_method) {
                this._addBulkActions(listview, config);
            }
            
            if (config.showExportOptions && config.export_base) {
                this._addExportOptions(listview, config);
            }
            
            if (this.global.enableWelcomeMsg) {
                this._addWelcomeMessage(listview, doctype);
            }
            
            listview.page.wrapper.on('list-view-updated', () => {
                if (config.showZebraStriping && this.global.zebraStriping) this._applyZebra();
                if (config.summary_method) this._refreshSummaryCards(listview, config);
                if (config.filter_method) this._refreshFilterCounts(config);
                if (config.onRefresh && typeof config.onRefresh === 'function') {
                    config.onRefresh(listview);
                }
            });
            
            setTimeout(() => {
                if (config.showZebraStriping && this.global.zebraStriping) this._applyZebra();
                if (this.global.enableAnimations) this._animateFadeIn();
            }, 150);
        },
        
        /**
         * Build summary cards
         */
        _buildSummaryCards(listview, config) {
            if ($('.ulv-summary-bar').length) return;
            
            const cards = [
                { id: 'total', emoji: '📊', icon: 'fa-chart-line', label: 'Total', color: '#0ea5e9' },
                { id: 'gross', emoji: '💰', icon: 'fa-money-bill-wave', label: 'Gross', color: '#22c55e' },
                { id: 'net', emoji: '📈', icon: 'fa-chart-simple', label: 'Net', color: '#f97316' },
                { id: 'unpaid', emoji: '⏳', icon: 'fa-hourglass-half', label: 'Unpaid', color: '#eab308' },
                { id: 'overdue', emoji: '🚨', icon: 'fa-exclamation-triangle', label: 'Overdue', color: '#ef4444' }
            ];
            
            const html = cards.map(c => `
                <div class="ulv-summary-card" style="--card-color: ${c.color}">
                    <div class="ulv-card-header">
                        <span class="ulv-card-emoji">${c.emoji}</span>
                        <i class="fa ${c.icon} ulv-card-icon"></i>
                    </div>
                    <div class="ulv-card-label">${__(c.label)}</div>
                    <div class="ulv-card-value" id="ulv-val-${c.id}">
                        <span class="ulv-card-shimmer">—</span>
                    </div>
                    <div class="ulv-card-count" id="ulv-cnt-${c.id}">
                        <i class="fa fa-spinner fa-spin"></i> loading...
                    </div>
                </div>
            `).join('');
            
            listview.page.wrapper.find('.layout-main-section')
                .prepend(`<div class="ulv-summary-bar">${html}</div>`);
            
            this._refreshSummaryCards(listview, config);
        },
        
        /**
         * Refresh summary cards data
         */
        _refreshSummaryCards(listview, config) {
            if (!config.summary_method) return;
            
            frappe.call({
                method: config.summary_method,
                callback: (r) => {
                    if (!r.message) return;
                    const data = r.message;
                    const currency = data.currency || '';
                    
                    const cards = ['total', 'gross', 'net', 'unpaid', 'overdue'];
                    cards.forEach(cardId => {
                        const amount = data[cardId + '_premium'] || data[cardId + '_amount'] || 0;
                        const count = data[cardId + '_count'] || 0;
                        
                        $(`#ulv-val-${cardId}`).html(_formatCompactCurrency(amount, currency));
                        const countText = count === 0 ? '✨ no records' : 
                                         count === 1 ? '🌟 1 record' : 
                                         `📋 ${count.toLocaleString()} records`;
                        $(`#ulv-cnt-${cardId}`).html(countText);
                    });
                }
            });
        },
        
        /**
         * Build quick filter chips
         */
        _buildQuickFilters(listview, doctype, config) {
            if ($('.ulv-filter-bar').length) return;
            
            const defaultFilters = [
                { key: 'all', emoji: '💖', icon: 'fa-heart', label: 'All', rules: null, color: '#8b5cf6' },
                { key: 'unpaid', emoji: '⏳', icon: 'fa-hourglass-half', label: 'Unpaid', 
                  rules: [[doctype, 'docstatus', '=', 1], [doctype, config.paid_field, 'is', 'not set']], color: '#f59e0b' },
                { key: 'paid', emoji: '✅', icon: 'fa-check-circle', label: 'Paid', 
                  rules: [[doctype, 'docstatus', '=', 1], [doctype, config.paid_field, 'is', 'set']], color: '#10b981' }
            ];
            
            const filters = config.quick_filters.length ? config.quick_filters : defaultFilters;
            
            const html = filters.map(f => `
                <div class="ulv-chip ${f.key === 'all' ? 'active' : ''}" 
                     data-filter="${f.key}" style="--chip-color: ${f.color}">
                    <span class="ulv-chip-emoji">${f.emoji}</span>
                    <i class="fa ${f.icon}"></i>
                    <span>${__(f.label)}</span>
                    <span class="ulv-chip-count">0</span>
                </div>
            `).join('');
            
            listview.page.wrapper.find('.layout-main-section')
                .prepend(`<div class="ulv-filter-bar">${html}</div>`);
            
            this._refreshFilterCounts(config);
            
            $(document).on('click', '.ulv-chip', function() {
                $('.ulv-chip').removeClass('active');
                $(this).addClass('active');
                const key = $(this).data('filter');
                const filter = filters.find(f => f.key === key);
                
                listview.filter_area.clear();
                if (filter && filter.rules) listview.filter_area.add(filter.rules);
                listview.refresh();
            });
        },
        
        /**
         * Refresh filter counts
         */
        _refreshFilterCounts(config) {
            if (!config.filter_method) return;
            frappe.call({
                method: config.filter_method,
                callback: (r) => {
                    if (!r.message) return;
                    Object.entries(r.message).forEach(([key, val]) => {
                        $(`.ulv-chip[data-filter="${key}"] .ulv-chip-count`).text(val);
                    });
                }
            });
        },
        
        /**
         * Add bulk actions
         */
        _addBulkActions(listview, config) {
            if (!config.send_method) return;
            
            listview.page.add_action_item('📧 Send Documents', () => {
                const selected = listview.get_checked_items();
                if (!selected.length) {
                    frappe.msgprint('💝 Please select at least one record to send!');
                    return;
                }
                
                frappe.confirm(`📨 Send documents for ${selected.length} record(s)?`, () => {
                    frappe.show_progress('Sending', 0, selected.length, 'Sending with love...');
                    let completed = 0;
                    
                    selected.forEach((doc, i) => {
                        setTimeout(() => {
                            frappe.call({
                                method: config.send_method,
                                args: { name: doc.name },
                                callback: () => {
                                    completed++;
                                    frappe.show_progress('Sending', completed, selected.length);
                                    if (completed === selected.length) {
                                        frappe.hide_progress();
                                        frappe.show_alert({ message: '🎉 All documents sent successfully! 🎉', indicator: 'green' }, 5);
                                        if (this.global.enableConfetti) this._fakeConfetti();
                                    }
                                }
                            });
                        }, i * 300);
                    });
                });
            });
        },
        
        /**
         * Add export options
         */
        _addExportOptions(listview, config) {
            if (!config.export_base) return;
            
            listview.page.add_menu_item('📊 Generate Report', () => {
                window.open(`${config.export_base}.download_report`, '_blank');
            });
            
            listview.page.add_menu_item('📑 Export to Excel', () => {
                const selected = listview.get_checked_items();
                const query = selected.length ? `?names=${selected.map(d => d.name).join(',')}` : '';
                window.open(`${config.export_base}.download_excel_report${query}`, '_blank');
            });
            
            listview.page.add_menu_item('📄 Export to PDF', () => {
                window.open(`${config.export_base}.download_pdf_report`, '_blank');
            });
        },
        
        /**
         * Add welcome message
         */
        _addWelcomeMessage(listview, doctype) {
            if ($('.ulv-welcome').length) return;
            
            const message = `
                <div class="ulv-welcome" style="display:none;">
                    <div class="ulv-welcome-content">
                        <span class="ulv-welcome-emoji">🎉</span>
                        <span>Welcome to ${doctype}! 🌟</span>
                        <button class="btn btn-xs btn-default ulv-dismiss">Got it ✨</button>
                    </div>
                </div>
            `;
            
            listview.page.wrapper.find('.layout-main-section').prepend(message);
            
            if (!sessionStorage.getItem(`ulv_welcome_${doctype}`)) {
                $('.ulv-welcome').fadeIn(300).delay(3000).fadeOut(500);
                sessionStorage.setItem(`ulv_welcome_${doctype}`, 'true');
            }
            
            $(document).on('click', '.ulv-dismiss', function() {
                $('.ulv-welcome').fadeOut(200);
            });
        },
        
        /**
         * Show row actions dialog
         */
        _showRowActions(doc, doctype, config) {
            const actions = [
                { emoji: '👁️', label: 'View', fn: () => frappe.set_route('Form', doctype, doc.name) }
            ];
            
            if (doc.docstatus === 1 && !doc[config.paid_field]) {
                actions.push({
                    emoji: '💰',
                    label: 'Record Payment',
                    fn: () => frappe.prompt(
                        { label: 'Receipt Number', fieldname: 'receipt', fieldtype: 'Data', reqd: 1 },
                        (vals) => frappe.call({
                            method: 'frappe.client.set_value',
                            args: { doctype, name: doc.name, fieldname: config.paid_field, value: vals.receipt },
                            callback: () => {
                                frappe.show_alert({ message: '✅ Payment recorded! 🎉', indicator: 'green' });
                                cur_list.refresh();
                                if (this.global.enableConfetti) this._fakeConfetti();
                            }
                        }),
                        'Record Payment 💳'
                    )
                });
            }
            
            if (doc.docstatus === 1 && config.send_method) {
                actions.push({
                    emoji: '📧',
                    label: 'Send Document',
                    fn: () => frappe.call({
                        method: config.send_method,
                        args: { name: doc.name },
                        callback: () => frappe.show_alert({ message: '📨 Sent with love! ✨', indicator: 'green' })
                    })
                });
            }
            
            if (doc.docstatus === 1) {
                actions.push(
                    { emoji: '🖨️', label: 'Print', fn: () => frappe.ui.form.print(doctype, doc.name) },
                    { emoji: '📋', label: 'Duplicate', fn: () => frappe.model.open_mapped_doc({ 
                        method: 'frappe.client.duplicate_doc', 
                        args: { doctype, name: doc.name } 
                    })}
                );
            }
            
            const html = actions.map(a => `
                <div class="ulv-action-item">
                    <span class="ulv-action-emoji">${a.emoji}</span>
                    <span>${a.label}</span>
                    <i class="fa fa-chevron-right ulv-action-arrow"></i>
                </div>
            `).join('');
            
            const dialog = new frappe.ui.Dialog({
                title: '✨ Quick Actions ✨',
                fields: [{ fieldtype: 'HTML', fieldname: 'html', options: `<div class="ulv-action-list">${html}</div>` }]
            });
            dialog.show();
            
            dialog.$wrapper.find('.ulv-action-item').each((i, el) => {
                $(el).on('click', () => {
                    actions[i].fn();
                    dialog.hide();
                });
            });
        },
        
        /**
         * Apply zebra striping
         */
        _applyZebra() {
            $('.list-row').each(function(i) {
                $(this)
                    .attr('data-row-index', i)
                    .toggleClass('ulv-row-odd', i % 2 !== 0)
                    .toggleClass('ulv-row-even', i % 2 === 0);
            });
        },
        
        /**
         * Animate fade in
         */
        _animateFadeIn() {
            $('.list-row').css('animation', 'fadeInUp 0.2s ease-out');
        },
        
        /**
         * Fake confetti effect
         */
        _fakeConfetti() {
            for (let i = 0; i < 30; i++) {
                const confetti = $('<div class="ulv-confetti">🎉</div>');
                $('body').append(confetti);
                confetti.css({
                    position: 'fixed',
                    left: Math.random() * window.innerWidth + 'px',
                    top: '-20px',
                    'font-size': (10 + Math.random() * 20) + 'px',
                    'z-index': 9999,
                    'pointer-events': 'none'
                });
                confetti.animate({
                    top: window.innerHeight + 'px',
                    left: (Math.random() * window.innerWidth) + 'px'
                }, 1000 + Math.random() * 1000, function() {
                    $(this).remove();
                });
            }
        },
        
        /**
         * Inject CSS styles
         */
        _injectStyles() {
            if (this.global.stylesInjected) return;
            
            const styles = `
            <style id="ulv-styles">
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                .list-headers {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                    color: #fff !important;
                    font-weight: 700;
                    text-transform: uppercase;
                    font-size: 11px;
                    letter-spacing: 1.2px;
                    padding: 14px 15px !important;
                    border-radius: 12px 12px 0 0 !important;
                }
                
                .list-row {
                    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                    border-left: 3px solid transparent;
                    cursor: pointer;
                }
                
                .list-row.ulv-row-even { background: #ffffff !important; }
                .list-row.ulv-row-odd { background: #fafbff !important; }
                
                .list-row[data-docstatus="0"] { 
                    background: linear-gradient(90deg, #fffbeb 0%, #fff 100%) !important; 
                    border-left-color: #f59e0b !important;
                }
                
                .list-row[data-docstatus="2"] { 
                    opacity: 0.5; 
                    background: #f3f4f6 !important;
                }
                
                .list-row:hover {
                    background: linear-gradient(90deg, #eef2ff 0%, #fff 100%) !important;
                    border-left-color: #8b5cf6 !important;
                    box-shadow: 0 4px 12px rgba(107, 70, 193, 0.15);
                    transform: translateX(4px);
                    z-index: 2;
                }
                
                .indicator-pill {
                    padding: 4px 12px !important;
                    border-radius: 20px !important;
                    font-weight: 700 !important;
                    font-size: 10px !important;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .indicator-pill.green { 
                    background: linear-gradient(135deg, #d1fae5, #a7f3d0); 
                    color: #065f46; 
                }
                
                .indicator-pill.blue { 
                    background: linear-gradient(135deg, #dbeafe, #bfdbfe); 
                    color: #1e40af; 
                }
                
                .indicator-pill.orange { 
                    background: linear-gradient(135deg, #ffedd5, #fed7aa); 
                    color: #9a3412; 
                }
                
                .indicator-pill.red { 
                    background: linear-gradient(135deg, #fee2e2, #fecaca); 
                    color: #991b1b; 
                }
                
                .ulv-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 11px;
                    font-weight: 600;
                    transition: all 0.2s;
                }
                
                .ulv-badge:hover {
                    transform: scale(1.02);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .ulv-summary-bar {
                    display: grid;
                    grid-template-columns: repeat(5, 1fr);
                    gap: 14px;
                    padding: 16px;
                    margin-bottom: 20px;
                    background: transparent;
                }
                
                .ulv-summary-card {
                    background: white;
                    border-radius: 16px;
                    padding: 16px 12px;
                    text-align: center;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    border: 1px solid rgba(0,0,0,0.05);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                    cursor: pointer;
                    position: relative;
                    overflow: hidden;
                }
                
                .ulv-summary-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: var(--card-color, #667eea);
                    transform: scaleX(0);
                    transition: transform 0.3s;
                }
                
                .ulv-summary-card:hover::before {
                    transform: scaleX(1);
                }
                
                .ulv-summary-card:hover {
                    transform: translateY(-6px);
                    box-shadow: 0 12px 24px rgba(0,0,0,0.12);
                }
                
                .ulv-card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                }
                
                .ulv-card-emoji { font-size: 28px; }
                .ulv-card-icon { font-size: 20px; color: var(--card-color); opacity: 0.6; }
                .ulv-card-label { 
                    font-size: 11px; 
                    text-transform: uppercase; 
                    letter-spacing: 1px;
                    color: #6b7280;
                    font-weight: 700;
                    margin-bottom: 8px;
                }
                .ulv-card-value { 
                    font-size: 24px; 
                    font-weight: 800; 
                    color: #1f2937;
                    margin: 8px 0;
                }
                .ulv-card-count { 
                    font-size: 11px; 
                    color: #9ca3af;
                    font-weight: 500;
                }
                
                .ulv-filter-bar {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    padding: 12px 16px;
                    background: white;
                    border-radius: 16px;
                    margin-bottom: 16px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                }
                
                .ulv-chip {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 6px 14px;
                    border-radius: 24px;
                    background: #f9fafb;
                    cursor: pointer;
                    font-size: 12px;
                    font-weight: 600;
                    color: #4b5563;
                    transition: all 0.2s;
                    border: 1px solid #e5e7eb;
                }
                
                .ulv-chip:hover {
                    transform: translateY(-2px);
                    border-color: var(--chip-color, #8b5cf6);
                    background: #f3f4f6;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.08);
                }
                
                .ulv-chip.active {
                    background: var(--chip-color, #8b5cf6);
                    color: white;
                    border-color: var(--chip-color, #8b5cf6);
                    box-shadow: 0 4px 12px rgba(107, 70, 193, 0.3);
                }
                
                .ulv-chip.active .ulv-chip-count {
                    background: rgba(255,255,255,0.25);
                }
                
                .ulv-chip-count {
                    display: inline-block;
                    padding: 2px 8px;
                    background: rgba(0,0,0,0.08);
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: 700;
                    min-width: 20px;
                    text-align: center;
                }
                
                .ulv-series {
                    font-weight: 700;
                    color: #1f2937;
                    font-size: 13px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .ulv-amount-primary {
                    font-weight: 800;
                    color: #059669;
                    font-size: 14px;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                
                .ulv-amount-secondary {
                    font-weight: 600;
                    color: #6b7280;
                    font-size: 12px;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                
                .ulv-date {
                    font-size: 12px;
                    color: #6b7280;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                
                .ulv-date-overdue {
                    color: #dc2626 !important;
                    font-weight: 700;
                }
                
                .ulv-date-soon {
                    color: #f97316 !important;
                    font-weight: 700;
                }
                
                .ulv-day-tag {
                    font-size: 10px;
                    padding: 2px 6px;
                    background: rgba(0,0,0,0.05);
                    border-radius: 12px;
                    margin-left: 4px;
                    font-weight: 600;
                }
                
                .ulv-icon-accent {
                    color: #8b5cf6;
                    width: 18px;
                    text-align: center;
                }
                
                .ulv-action-list {
                    padding: 4px;
                    max-height: 400px;
                    overflow-y: auto;
                }
                
                .ulv-action-item {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 12px 16px;
                    cursor: pointer;
                    border-radius: 12px;
                    font-size: 13px;
                    font-weight: 500;
                    color: #374151;
                    transition: all 0.15s;
                    margin: 4px 0;
                }
                
                .ulv-action-emoji { font-size: 16px; margin-right: 12px; }
                .ulv-action-arrow { opacity: 0; transition: opacity 0.2s, transform 0.2s; }
                
                .ulv-action-item:hover .ulv-action-arrow {
                    opacity: 1;
                    transform: translateX(4px);
                }
                
                .ulv-action-item:hover {
                    background: linear-gradient(90deg, #f3f4f6 0%, #fff 100%);
                    transform: translateX(4px);
                }
                
                .ulv-welcome {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 20px;
                    border-radius: 12px;
                    margin-bottom: 16px;
                    animation: fadeInUp 0.4s ease;
                }
                
                .ulv-welcome-content {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 16px;
                }
                
                .ulv-welcome-emoji { font-size: 24px; }
                
                .ulv-dismiss {
                    background: rgba(255,255,255,0.2);
                    border: 1px solid rgba(255,255,255,0.3);
                    color: white;
                    padding: 4px 12px;
                    border-radius: 20px;
                    transition: all 0.2s;
                }
                
                .ulv-dismiss:hover {
                    background: rgba(255,255,255,0.3);
                    transform: scale(1.02);
                }
                
                @media (max-width: 1024px) {
                    .ulv-summary-bar { grid-template-columns: repeat(3, 1fr); }
                }
                
                @media (max-width: 640px) {
                    .ulv-summary-bar { grid-template-columns: repeat(2, 1fr); }
                }
            </style>`;
            
            $('head').append(styles);
            this.global.stylesInjected = true;
        },
        
        /**
         * Configure global settings
         */
        configure(settings) {
            Object.assign(this.global, settings);
            if (this.global.debug) {
                console.log('[ULV] Global settings updated:', this.global);
            }
        },
        
        /**
         * Get configuration for a doctype
         */
        getConfig(doctype) {
            return this.doctypes[doctype] || null;
        },
        
        /**
         * Reload listview for a doctype
         */
        reload(doctype) {
            if (frappe.listview_settings[doctype]) {
                this._applyToDoctype(doctype);
                if (this.global.debug) console.log(`[ULV] Reloaded ${doctype}`);
            }
        },
        
        /**
         * Get all registered doctypes
         */
        getRegisteredDoctypes() {
            return Object.keys(this.doctypes);
        }
    };
    
    // ============================================================
    //  🚀 EXPOSE GLOBALLY
    // ============================================================
    
    window.UniversalListView = {
        register: (doctype, config) => UniversalListViewConfig.register(doctype, config),
        registerBatch: (configs) => UniversalListViewConfig.registerBatch(configs),
        configure: (settings) => UniversalListViewConfig.configure(settings),
        getConfig: (doctype) => UniversalListViewConfig.getConfig(doctype),
        reload: (doctype) => UniversalListViewConfig.reload(doctype),
        getRegistered: () => UniversalListViewConfig.getRegisteredDoctypes(),
        version: '2.0.0'
    };
    
})();

// ============================================================
//  📋 DEFAULT CONFIGURATIONS FOR COMMON DOCTYPES
//  Add your own configurations here or in separate files
// ============================================================

// Example configurations - uncomment and customize for your doctypes
/*
UniversalListView.registerBatch({
    'Debit Note': {
        add_fields: ['naming_series', 'posting_date', 'due_date', 'insured_name', 
                     'insurer_name', 'gross_premium', 'net_premium', 'currency', 
                     'receipt_no', 'insurance_class_group', 'docstatus'],
        amount_fields: ['gross_premium', 'net_premium'],
        badge_fields: ['insurance_class_group'],
        series_field: 'naming_series',
        date_fields: ['posting_date', 'due_date'],
        due_date_field: 'due_date',
        paid_field: 'receipt_no',
        currency_field: 'currency',
        filters: [['docstatus', '!=', 2]],
        summary_method: 'your_app.your_module.doctype.debit_note.debit_note.get_summary',
        filter_method: 'your_app.your_module.doctype.debit_note.debit_note.get_filters',
        send_method: 'your_app.your_module.doctype.debit_note.debit_note.send_document',
        export_base: '/api/method/your_app.your_module.doctype.debit_note.debit_note'
    },
    
    'Sales Invoice': {
        add_fields: ['naming_series', 'customer', 'posting_date', 'due_date', 
                     'grand_total', 'outstanding_amount', 'currency', 'status', 'docstatus'],
        amount_fields: ['grand_total', 'outstanding_amount'],
        badge_fields: ['status'],
        series_field: 'naming_series',
        date_fields: ['posting_date', 'due_date'],
        due_date_field: 'due_date',
        paid_field: 'outstanding_amount',
        currency_field: 'currency',
        filters: [['docstatus', '!=', 2]],
        summary_method: 'accounts.accounts.doctype.sales_invoice.sales_invoice.get_summary',
        filter_method: 'accounts.accounts.doctype.sales_invoice.sales_invoice.get_filters',
        export_base: '/api/method/accounts.accounts.doctype.sales_invoice.sales_invoice'
    },
    
    'Purchase Order': {
        add_fields: ['naming_series', 'supplier', 'transaction_date', 'schedule_date',
                     'grand_total', 'currency', 'status', 'docstatus'],
        amount_fields: ['grand_total'],
        badge_fields: ['status'],
        series_field: 'naming_series',
        date_fields: ['transaction_date', 'schedule_date'],
        due_date_field: 'schedule_date',
        paid_field: 'per_received',
        currency_field: 'currency',
        filters: [['docstatus', '!=', 2]],
        summary_method: 'buying.buying.doctype.purchase_order.purchase_order.get_summary',
        export_base: '/api/method/buying.buying.doctype.purchase_order.purchase_order'
    }
});

// Global configuration
UniversalListView.configure({
    enabled: true,
    debug: false,
    enableAnimations: true,
    enableConfetti: true,
    enableWelcomeMsg: true
});
*/