// broker/broker/page/desktop-shc/desktop-shc.js
// Desktop-SHC — Insurance Broker ERP Desktop Shortcuts
// Organized in 3-column vertical layout with 15 functional groups

frappe.pages['desktop-shc'] = frappe.pages['desktop-shc'] || {};

frappe.pages['desktop-shc'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '🖥️ Desktop-SHC',
        single_column: true
    });

    // ─── Themes ──────────────────────────────────────────────────────────────
    const THEMES = {
        corporate: {
            name: 'Corporate', primary: '#1E293B', accent: '#3B82F6',
            bg: '#F8FAFC', card: '#FFFFFF', text: '#0F172A',
            muted: '#64748B', border: '#E2E8F0',
            gradient: 'linear-gradient(135deg,#1E293B 0%,#3B82F6 100%)',
            sectionBg: 'rgba(59,130,246,0.04)'
        },
        emerald: {
            name: 'Emerald', primary: '#065F46', accent: '#34D399',
            bg: '#ECFDF5', card: '#FFFFFF', text: '#022C22',
            muted: '#047857', border: '#A7F3D0',
            gradient: 'linear-gradient(135deg,#022C22 0%,#059669 50%,#34D399 100%)',
            sectionBg: 'rgba(5,150,105,0.06)'
        },
        royal: {
            name: 'Royal', primary: '#4C1D95', accent: '#A78BFA',
            bg: '#FAF5FF', card: '#FFFFFF', text: '#2E1065',
            muted: '#6D28D9', border: '#E9D5FF',
            gradient: 'linear-gradient(135deg,#1E1B4B 0%,#7C3AED 50%,#A78BFA 100%)',
            sectionBg: 'rgba(124,58,237,0.06)'
        },
        sunset: {
            name: 'Sunset', primary: '#9A3412', accent: '#F97316',
            bg: '#FFF7ED', card: '#FFFFFF', text: '#431407',
            muted: '#9A3412', border: '#FED7AA',
            gradient: 'linear-gradient(135deg,#431407 0%,#EA580C 50%,#FBBF24 100%)',
            sectionBg: 'rgba(234,88,12,0.06)'
        },
        ocean: {
            name: 'Ocean', primary: '#0C4A6E', accent: '#38BDF8',
            bg: '#F0F9FF', card: '#FFFFFF', text: '#0C4A6E',
            muted: '#0369A1', border: '#BAE6FD',
            gradient: 'linear-gradient(135deg,#0C4A6E 0%,#0284C7 50%,#38BDF8 100%)',
            sectionBg: 'rgba(2,132,199,0.06)'
        },
        midnight: {
            name: 'Midnight', primary: '#0F172A', accent: '#818CF8',
            bg: '#0F172A', card: '#1E293B', text: '#F1F5F9',
            muted: '#94A3B8', border: '#334155',
            gradient: 'linear-gradient(135deg,#020617 0%,#1E293B 50%,#6366F1 100%)',
            sectionBg: 'rgba(99,102,241,0.08)'
        },
        forest: {
            name: 'Forest', primary: '#052E16', accent: '#22C55E',
            bg: '#052E16', card: '#14532D', text: '#F0FDF4',
            muted: '#86EFAC', border: '#166534',
            gradient: 'linear-gradient(135deg,#052E16 0%,#166534 50%,#22C55E 100%)',
            sectionBg: 'rgba(34,197,94,0.08)'
        }
    };

    const savedTheme = localStorage.getItem('desktop_shc_theme') || 'corporate';
    let currentTheme = savedTheme;

    // ─── SEARCH & FILTER ──────────────────────────────────────────────────────
    let searchFilter = '';

    // ─── 15 GROUPS (3 Columns x 5 Rows) ─────────────────────────────────────
    const GROUPS = [
        // Column 1
        {
            id: 'crm',
            name: '🤝 CRM & Sales',
            icon: '🤝',
            color: '#3B82F6',
            items: [
                { name: 'CRM Lead', icon: '🔹', color: '#3B82F6' },
                { name: 'CRM Opportunity', icon: '💎', color: '#F59E0B' },
                { name: 'CRM Deal', icon: '🤝', color: '#7C3AED' },
                { name: 'CRM Contact', icon: '👤', color: '#0284C7' },
                { name: 'CRM Account', icon: '🏢', color: '#6366F1' },
                { name: 'CRM Meeting', icon: '📅', color: '#F59E0B' },
                { name: 'CRM Activity', icon: '📝', color: '#10B981' },
                { name: 'CRM Pipeline', icon: '🔀', color: '#8B5CF6' },
                { name: 'CRM Deal Stage', icon: '📈', color: '#8B5CF6' },
                { name: 'CRM Source', icon: '🔗', color: '#3B82F6' },
                { name: 'CRM Territory', icon: '🌍', color: '#10B981' },
                { name: 'CRM Quota Target', icon: '🎯', color: '#EF4444' }
            ]
        },
        {
            id: 'audit',
            name: '🔍 Audit Management',
            icon: '🔍',
            color: '#F43F5E',
            items: [
                { name: 'Annual Audit Plan', icon: '📅', color: '#7C3AED' },
                { name: 'Audit Universe', icon: '🌌', color: '#8B5CF6' },
                { name: 'Audit Engagement', icon: '🤝', color: '#6D28D9' },
                { name: 'Audit Checklist', icon: '✅', color: '#4C1D95' },
                { name: 'Audit Finding', icon: '🔍', color: '#EF4444' },
                { name: 'Audit Report', icon: '📄', color: '#DC2626' },
                { name: 'Corrective Action Plan', icon: '📋', color: '#F59E0B' }
            ]
        },
        {
            id: 'hr',
            name: '👤 HR & Employee Services',
            icon: '👤',
            color: '#6366F1',
            items: [
                { name: 'Employee Document', icon: '📁', color: '#6366F1' },
                { name: 'Employee Loan Application', icon: '📋', color: '#059669' },
                { name: 'Loan Repayment Entry', icon: '💳', color: '#0284C7' },
                { name: 'Staff Loan Payment', icon: '💵', color: '#16A34A' },
                { name: 'ESS Task', icon: '✅', color: '#5B21B6' },
                { name: 'ESS Activity Log', icon: '📋', color: '#7C3AED' },
                { name: 'Company Policy', icon: '📜', color: '#7C3AED' },
                { name: 'Policy Acknowledgement', icon: '✍️', color: '#10B981' },
                { name: 'Performance Cycle', icon: '🔄', color: '#8B5CF6' },
                { name: 'Employee Performance Record', icon: '⭐', color: '#F59E0B' }
            ]
        },
        {
            id: 'facility',
            name: '🏢 Facility & Administration',
            icon: '🏢',
            color: '#8B5CF6',
            items: [
                { name: 'Facility', icon: '🏭', color: '#6366F1' },
                { name: 'Facility Maintenance Request', icon: '🔧', color: '#F97316' },
                { name: 'Meeting Room Booking', icon: '🏢', color: '#8B5CF6' },
                { name: 'Administrative Request', icon: '📋', color: '#6B7280' },
                { name: 'Visitor Register', icon: '📕', color: '#6B7280' },
                { name: 'Security Incident', icon: '🚨', color: '#EF4444' },
                { name: 'Service Provider', icon: '🔧', color: '#8B5CF6' },
                { name: 'Service Contract', icon: '📄', color: '#10B981' },
                { name: 'eRequest', icon: '📨', color: '#6366F1' }
            ]
        },
        {
            id: 'inventory',
            name: '📦 Inventory & POS',
            icon: '📦',
            color: '#059669',
            items: [
                { name: 'Stock Availability', icon: '📦', color: '#D97706' },
                { name: 'Stock Balance Reconciliation', icon: '📊', color: '#059669' },
                { name: 'ECC POS Settings', icon: '🖥️', color: '#6366F1' }
            ]
        },

        // Column 2
        {
            id: 'compliance',
            name: '📜 Compliance & Regulatory',
            icon: '📜',
            color: '#7C3AED',
            items: [
                { name: 'Compliance Dashboard', icon: '📊', color: '#7C3AED' },
                { name: 'Compliance Filing', icon: '📄', color: '#3B82F6' },
                { name: 'Regulatory Return', icon: '📤', color: '#EA580C' },
                { name: 'AML KYC Record', icon: '🛡️', color: '#059669' },
                { name: 'Suspicious Transaction Report', icon: '🚩', color: '#DC2626' },
                { name: 'Compliance Audit', icon: '🔍', color: '#F43F5E' },
                { name: 'Compliance Incident', icon: '🚨', color: '#EF4444' },
                { name: 'Compliance Risk Register', icon: '⚠️', color: '#F97316' },
                { name: 'Compliance Task', icon: '✅', color: '#22C55E' },
                { name: 'Compliance Exception', icon: '❌', color: '#DC2626' },
                { name: 'Compliance Calendar', icon: '📅', color: '#7C3AED' },
                { name: 'Regulatory Authority', icon: '🏛️', color: '#DC2626' },
                { name: 'Whistleblower Report', icon: '🔊', color: '#EF4444' },
                { name: 'Board Resolution', icon: '📜', color: '#7C3AED' }
            ]
        },
        {
            id: 'finance',
            name: '💰 Finance & Treasury',
            icon: '💰',
            color: '#059669',
            items: [
                { name: 'Payments', icon: '💵', color: '#10B981' },
                { name: 'Receipts', icon: '🧾', color: '#0284C7' },
                { name: 'Payment Batch', icon: '💳', color: '#059669' },
                { name: 'Bank Reconciliation', icon: '🏦', color: '#059669' },
                { name: 'Bank Reconciliation Statement', icon: '📊', color: '#10B981' },
                { name: 'Bank Statement Upload', icon: '📤', color: '#0284C7' },
                { name: 'Journal Entry Voucher', icon: '🧾', color: '#8B5CF6' },
                { name: 'Expense Batch', icon: '📦', color: '#EF4444' },
                { name: 'Accruals', icon: '📋', color: '#F59E0B' },
                { name: 'Financial Report Template', icon: '📄', color: '#8B5CF6' }
            ]
        },
        {
            id: 'fixed_asset',
            name: '🏗️ Fixed Asset Management',
            icon: '🏗️',
            color: '#6366F1',
            items: [
                { name: 'Fixed Asset', icon: '🏗️', color: '#6366F1' },
                { name: 'Fixed Asset Purchase', icon: '🛒', color: '#059669' },
                { name: 'Fixed Asset Transfer', icon: '🔄', color: '#F59E0B' },
                { name: 'Fixed Asset Revaluation', icon: '📈', color: '#0284C7' },
                { name: 'Fixed Asset Insurance', icon: '🛡️', color: '#7C3AED' },
                { name: 'Fixed Asset Maintenance', icon: '🔧', color: '#F97316' },
                { name: 'Fixed Asset Disposal', icon: '🗑️', color: '#EF4444' },
                { name: 'Fixed Asset Verification', icon: '✅', color: '#22C55E' },
                { name: 'Fixed Asset Category', icon: '📂', color: '#8B5CF6' }
            ]
        },
        {
            id: 'fleet',
            name: '🚗 Fleet & Fuel Management',
            icon: '🚗',
            color: '#059669',
            items: [
                { name: 'Company Vehicle', icon: '🚗', color: '#059669' },
                { name: 'Vehicle Request', icon: '📋', color: '#F59E0B' },
                { name: 'Vehicle Trip Log', icon: '📝', color: '#D97706' },
                { name: 'Fuel Issue', icon: '⛽', color: '#F97316' },
                { name: 'Generator Log', icon: '⚡', color: '#DC2626' }
            ]
        },
        {
            id: 'budget',
            name: '📊 Budget & Planning',
            icon: '📊',
            color: '#059669',
            items: [
                { name: 'Annual Budget', icon: '📆', color: '#0284C7' },
                { name: 'Budget Plan', icon: '📊', color: '#059669' },
                { name: 'Budget Settings', icon: '⚙️', color: '#4B5563' }
            ]
        },

        // Column 3
        {
            id: 'wfh',
            name: '🏠 Work From Home',
            icon: '🏠',
            color: '#F59E0B',
            items: [
                { name: 'WFH Request', icon: '📋', color: '#F97316' },
                { name: 'WFH Schedule', icon: '🏠', color: '#F59E0B' },
                { name: 'WFH Session', icon: '🖥️', color: '#D97706' },
                { name: 'WFH Daily Summary', icon: '📊', color: '#EA580C' },
                { name: 'Work Session', icon: '💻', color: '#059669' },
                { name: 'Work Activity Log', icon: '📝', color: '#6B7280' }
            ]
        },
        {
            id: 'statutory',
            name: '📋 Statutory Remittance',
            icon: '📋',
            color: '#7C3AED',
            items: [
                { name: 'Pension Remittance Batch', icon: '🏦', color: '#059669' },
                { name: 'Pension Manager', icon: '👤', color: '#0D9488' },
                { name: 'NHF Remittance Batch', icon: '🏠', color: '#D97706' },
                { name: 'NSITF Assessment', icon: '📋', color: '#EF4444' },
                { name: 'ITF Assessment', icon: '📊', color: '#F59E0B' },
                { name: 'Employee Tax Computation', icon: '🧾', color: '#DC2626' }
            ]
        },
        {
            id: 'communication',
            name: '💬 Customer Communication',
            icon: '💬',
            color: '#25D366',
            items: [
                { name: 'Message Blast', icon: '📨', color: '#F59E0B' },
                { name: 'Contact Us', icon: '📧', color: '#10B981' },
                { name: 'Social Post', icon: '📱', color: '#EC4899' },
                { name: 'WA Conversation', icon: '🗣️', color: '#25D366' },
                { name: 'WA Message', icon: '📨', color: '#128C7E' },
                { name: 'WA Broadcast', icon: '📢', color: '#25D366' },
                { name: 'Telephone Call Log', icon: '📞', color: '#3B82F6' },
                { name: 'Communique', icon: '📢', color: '#8B5CF6' }
            ]
        },
        {
            id: 'system',
            name: '⚙️ System Administration',
            icon: '⚙️',
            color: '#475569',
            items: [
                { name: 'Doctype Creator', icon: '🛠️', color: '#8B5CF6' },
                { name: 'Bulk Import Template', icon: '📄', color: '#8B5CF6' },
                { name: 'Bulk Import Log', icon: '📋', color: '#6B7280' },
                { name: 'Web Form Settings', icon: '🌐', color: '#3B82F6' },
                { name: 'Audit Trail Settings', icon: '🔒', color: '#1E293B' },
                { name: 'System Integrity Log', icon: '📊', color: '#4B5563' },
                { name: 'Document Audit Log', icon: '📝', color: '#6B7280' },
                { name: 'Doctype Export', icon: '📤', color: '#059669' }
            ]
        },
        {
            id: 'dashboard',
            name: '📊 Management Dashboard',
            icon: '📊',
            color: '#8B5CF6',
            items: [
                { name: 'Compliance KPI Snapshot', icon: '📊', color: '#059669' },
                { name: 'Financial Reporting Group', icon: '📈', color: '#6366F1' },
                { name: 'Financial Report Template', icon: '📄', color: '#8B5CF6' },
                { name: 'Audit Report', icon: '📄', color: '#DC2626' },
                { name: 'CRM Pipeline', icon: '🔀', color: '#8B5CF6' },
                { name: 'Ecclesia Investment', icon: '📈', color: '#059669' }
            ]
        }
    ];

    // ─── Build HTML ──────────────────────────────────────────────────────────
    const totalItems = GROUPS.reduce((acc, g) => acc + g.items.length, 0);

    const html = `
        <div id="desktop-shc-root">
            <!-- Top Bar -->
            <div class="desktop-shc-top-bar">
                <div class="desktop-shc-brand">
                    <span class="brand-icon">🖥️</span>
                    <span class="brand-name">Desktop-SHC</span>
                    <span class="brand-version">v1.0</span>
                    <span class="brand-badge">Insurance Broker ERP</span>
                </div>
                <div class="desktop-shc-controls">
                    <div class="desktop-shc-theme-selector">
                        ${Object.entries(THEMES).map(([key, t]) => `
                            <button class="theme-btn ${key === currentTheme ? 'active' : ''}" 
                                    data-theme="${key}" title="${t.name}"
                                    style="background: ${t.primary};">
                                <span class="theme-dot" style="background: ${t.accent};"></span>
                            </button>
                        `).join('')}
                    </div>
                    <div class="desktop-shc-search-wrapper">
                        <input type="text" id="desktop-shc-search" placeholder="Search shortcuts..." />
                        <span class="search-shortcut">⌘K</span>
                    </div>
                </div>
            </div>

            <!-- Stats Bar -->
            <div class="desktop-shc-stats">
                <div class="stat-card">
                    <span class="stat-icon">📂</span>
                    <span class="stat-number">${GROUPS.length}</span>
                    <span class="stat-label">Groups</span>
                </div>
                <div class="stat-card">
                    <span class="stat-icon">📋</span>
                    <span class="stat-number">${totalItems}</span>
                    <span class="stat-label">Shortcuts</span>
                </div>
                <div class="stat-card">
                    <span class="stat-icon">⭐</span>
                    <span class="stat-number" id="favorite-count">0</span>
                    <span class="stat-label">Favorites</span>
                </div>
                <div class="stat-card">
                    <span class="stat-icon">📊</span>
                    <span class="stat-number">${GROUPS.filter(g => g.id === 'dashboard').reduce((acc, g) => acc + g.items.length, 0)}</span>
                    <span class="stat-label">Dashboards</span>
                </div>
            </div>

            <!-- 3-Column Grid -->
            <div class="desktop-shc-grid" id="desktop-shc-grid">
                ${GROUPS.map(group => `
                    <div class="desktop-shc-group" data-group="${group.id}">
                        <div class="desktop-shc-group-header" style="border-color: ${group.color};">
                            <span class="group-icon">${group.icon}</span>
                            <span class="group-name">${group.name}</span>
                            <span class="group-count">${group.items.length}</span>
                        </div>
                        <div class="desktop-shc-group-body">
                            ${group.items.map(item => `
                                <div class="desktop-shc-item" 
                                     onclick="openDesktopItem('List', '${item.name}')"
                                     data-name="${item.name}">
                                    <button class="fav-btn" onclick="event.stopPropagation(); toggleFavorite('${item.name}')">☆</button>
                                    <div class="desktop-shc-item-icon" style="background:${item.color}22;color:${item.color}">
                                        ${item.icon}
                                    </div>
                                    <span class="desktop-shc-item-name">${item.name}</span>
                                    <span class="open-indicator">↗</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>

            <!-- Empty State -->
            <div class="desktop-shc-empty" id="desktop-shc-empty" style="display:none;">
                <div class="empty-icon">🔍</div>
                <h3>No results found</h3>
                <p>Try adjusting your search</p>
            </div>
        </div>

        <style>
            /* ─── Base ─────────────────────────────────────────────────────────── */
            #desktop-shc-root {
                padding: 16px 20px;
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background: var(--desktop-shc-bg, #F8FAFC);
                color: var(--desktop-shc-text, #0F172A);
                min-height: 100vh;
                transition: all 0.3s ease;
            }

            #desktop-shc-root[data-theme="corporate"] {
                --desktop-shc-primary: #1E293B; --desktop-shc-accent: #3B82F6;
                --desktop-shc-bg: #F8FAFC; --desktop-shc-card: #FFFFFF;
                --desktop-shc-text: #0F172A; --desktop-shc-muted: #64748B;
                --desktop-shc-border: #E2E8F0; --desktop-shc-section-bg: rgba(59,130,246,0.04);
                --desktop-shc-gradient: linear-gradient(135deg,#1E293B 0%,#3B82F6 100%);
            }
            #desktop-shc-root[data-theme="emerald"] {
                --desktop-shc-primary: #065F46; --desktop-shc-accent: #34D399;
                --desktop-shc-bg: #ECFDF5; --desktop-shc-card: #FFFFFF;
                --desktop-shc-text: #022C22; --desktop-shc-muted: #047857;
                --desktop-shc-border: #A7F3D0; --desktop-shc-section-bg: rgba(5,150,105,0.06);
                --desktop-shc-gradient: linear-gradient(135deg,#022C22 0%,#059669 50%,#34D399 100%);
            }
            #desktop-shc-root[data-theme="royal"] {
                --desktop-shc-primary: #4C1D95; --desktop-shc-accent: #A78BFA;
                --desktop-shc-bg: #FAF5FF; --desktop-shc-card: #FFFFFF;
                --desktop-shc-text: #2E1065; --desktop-shc-muted: #6D28D9;
                --desktop-shc-border: #E9D5FF; --desktop-shc-section-bg: rgba(124,58,237,0.06);
                --desktop-shc-gradient: linear-gradient(135deg,#1E1B4B 0%,#7C3AED 50%,#A78BFA 100%);
            }
            #desktop-shc-root[data-theme="sunset"] {
                --desktop-shc-primary: #9A3412; --desktop-shc-accent: #F97316;
                --desktop-shc-bg: #FFF7ED; --desktop-shc-card: #FFFFFF;
                --desktop-shc-text: #431407; --desktop-shc-muted: #9A3412;
                --desktop-shc-border: #FED7AA; --desktop-shc-section-bg: rgba(234,88,12,0.06);
                --desktop-shc-gradient: linear-gradient(135deg,#431407 0%,#EA580C 50%,#FBBF24 100%);
            }
            #desktop-shc-root[data-theme="ocean"] {
                --desktop-shc-primary: #0C4A6E; --desktop-shc-accent: #38BDF8;
                --desktop-shc-bg: #F0F9FF; --desktop-shc-card: #FFFFFF;
                --desktop-shc-text: #0C4A6E; --desktop-shc-muted: #0369A1;
                --desktop-shc-border: #BAE6FD; --desktop-shc-section-bg: rgba(2,132,199,0.06);
                --desktop-shc-gradient: linear-gradient(135deg,#0C4A6E 0%,#0284C7 50%,#38BDF8 100%);
            }
            #desktop-shc-root[data-theme="midnight"] {
                --desktop-shc-primary: #0F172A; --desktop-shc-accent: #818CF8;
                --desktop-shc-bg: #0F172A; --desktop-shc-card: #1E293B;
                --desktop-shc-text: #F1F5F9; --desktop-shc-muted: #94A3B8;
                --desktop-shc-border: #334155; --desktop-shc-section-bg: rgba(99,102,241,0.08);
                --desktop-shc-gradient: linear-gradient(135deg,#020617 0%,#1E293B 50%,#6366F1 100%);
            }
            #desktop-shc-root[data-theme="forest"] {
                --desktop-shc-primary: #052E16; --desktop-shc-accent: #22C55E;
                --desktop-shc-bg: #052E16; --desktop-shc-card: #14532D;
                --desktop-shc-text: #F0FDF4; --desktop-shc-muted: #86EFAC;
                --desktop-shc-border: #166534; --desktop-shc-section-bg: rgba(34,197,94,0.08);
                --desktop-shc-gradient: linear-gradient(135deg,#052E16 0%,#166534 50%,#22C55E 100%);
            }

            /* ─── Top Bar ──────────────────────────────────────────────────────── */
            .desktop-shc-top-bar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 16px;
                flex-wrap: wrap;
                background: var(--desktop-shc-card);
                padding: 12px 20px;
                border-radius: 16px;
                border: 1px solid var(--desktop-shc-border);
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }
            .desktop-shc-brand {
                display: flex;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
            }
            .brand-icon { font-size: 24px; }
            .brand-name {
                font-size: 18px;
                font-weight: 800;
                color: var(--desktop-shc-text);
            }
            .brand-version {
                font-size: 10px;
                font-weight: 600;
                color: var(--desktop-shc-muted);
                background: var(--desktop-shc-bg);
                padding: 2px 8px;
                border-radius: 12px;
            }
            .brand-badge {
                font-size: 9px;
                font-weight: 700;
                color: #fff;
                background: var(--desktop-shc-gradient);
                padding: 2px 12px;
                border-radius: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .desktop-shc-controls {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }
            .desktop-shc-theme-selector {
                display: flex;
                gap: 6px;
                align-items: center;
            }
            .theme-btn {
                width: 30px;
                height: 30px;
                border-radius: 50%;
                border: 2px solid transparent;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
            }
            .theme-btn:hover { transform: scale(1.1); }
            .theme-btn.active {
                border-color: var(--desktop-shc-accent);
                box-shadow: 0 0 0 3px var(--desktop-shc-accent)33;
            }
            .theme-dot { width: 14px; height: 14px; border-radius: 50%; display: block; }
            .desktop-shc-search-wrapper {
                position: relative;
                display: flex;
                align-items: center;
            }
            .desktop-shc-search-wrapper input {
                padding: 8px 16px;
                padding-right: 60px;
                border-radius: 24px;
                border: 1px solid var(--desktop-shc-border);
                background: var(--desktop-shc-bg);
                color: var(--desktop-shc-text);
                font-size: 13px;
                min-width: 200px;
                transition: all 0.2s;
                outline: none;
            }
            .desktop-shc-search-wrapper input:focus {
                border-color: var(--desktop-shc-accent);
                box-shadow: 0 0 0 3px var(--desktop-shc-accent)33;
            }
            .search-shortcut {
                position: absolute;
                right: 12px;
                font-size: 10px;
                color: var(--desktop-shc-muted);
                background: var(--desktop-shc-card);
                padding: 2px 8px;
                border-radius: 4px;
                border: 1px solid var(--desktop-shc-border);
                font-weight: 600;
                opacity: 0.6;
            }

            /* ─── Stats ───────────────────────────────────────────────────────── */
            .desktop-shc-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 10px;
                margin-bottom: 16px;
            }
            .stat-card {
                background: var(--desktop-shc-card);
                border: 1px solid var(--desktop-shc-border);
                border-radius: 12px;
                padding: 12px 16px;
                display: flex;
                align-items: center;
                gap: 10px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                transition: all 0.2s;
            }
            .stat-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.06);
            }
            .stat-icon { font-size: 20px; }
            .stat-number {
                font-size: 20px;
                font-weight: 800;
                color: var(--desktop-shc-text);
                font-feature-settings: "tnum";
            }
            .stat-label {
                font-size: 9px;
                font-weight: 500;
                color: var(--desktop-shc-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            /* ─── 3-Column Grid ───────────────────────────────────────────────── */
            .desktop-shc-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                align-items: start;
            }
            .desktop-shc-group {
                background: var(--desktop-shc-card);
                border-radius: 14px;
                border: 1px solid var(--desktop-shc-border);
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                transition: all 0.2s;
                display: flex;
                flex-direction: column;
            }
            .desktop-shc-group:hover {
                box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            }
            .desktop-shc-group-header {
                padding: 10px 14px;
                background: var(--desktop-shc-section-bg);
                border-bottom: 3px solid var(--group-color, var(--desktop-shc-accent));
                display: flex;
                align-items: center;
                gap: 8px;
                flex-shrink: 0;
            }
            .group-icon { font-size: 16px; }
            .group-name {
                font-weight: 700;
                font-size: 13px;
                color: var(--desktop-shc-text);
                flex: 1;
            }
            .group-count {
                font-size: 10px;
                font-weight: 600;
                color: var(--desktop-shc-muted);
                background: var(--desktop-shc-bg);
                padding: 1px 8px;
                border-radius: 12px;
            }
            .desktop-shc-group-body {
                padding: 8px 10px 10px;
                display: flex;
                flex-direction: column;
                gap: 3px;
                flex: 1;
            }

            /* ─── Items ───────────────────────────────────────────────────────── */
            .desktop-shc-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 5px 10px;
                border-radius: 8px;
                background: var(--desktop-shc-bg);
                border: 1px solid transparent;
                cursor: pointer;
                transition: all 0.15s;
                position: relative;
            }
            .desktop-shc-item:hover {
                border-color: var(--desktop-shc-accent);
                transform: translateX(3px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            }
            .desktop-shc-item .fav-btn {
                background: none;
                border: none;
                cursor: pointer;
                font-size: 11px;
                opacity: 0.2;
                transition: all 0.2s;
                padding: 0 2px;
                color: var(--desktop-shc-text);
            }
            .desktop-shc-item .fav-btn:hover { opacity: 1; transform: scale(1.2); }
            .desktop-shc-item .fav-btn.active { opacity: 1; color: #F59E0B; }
            .desktop-shc-item-icon {
                width: 26px;
                height: 26px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                flex-shrink: 0;
            }
            .desktop-shc-item-name {
                font-size: 11px;
                font-weight: 500;
                color: var(--desktop-shc-text);
                line-height: 1.3;
                flex: 1;
            }
            .desktop-shc-item .open-indicator {
                font-size: 9px;
                color: var(--desktop-shc-muted);
                opacity: 0.3;
                transition: opacity 0.2s;
            }
            .desktop-shc-item:hover .open-indicator { opacity: 1; }

            /* ─── Empty State ─────────────────────────────────────────────────── */
            .desktop-shc-empty {
                text-align: center;
                padding: 60px 20px;
                background: var(--desktop-shc-card);
                border-radius: 16px;
                border: 2px dashed var(--desktop-shc-border);
            }
            .empty-icon { font-size: 48px; margin-bottom: 12px; }
            .desktop-shc-empty h3 {
                font-size: 18px;
                color: var(--desktop-shc-text);
                margin: 0 0 8px 0;
            }
            .desktop-shc-empty p {
                color: var(--desktop-shc-muted);
                font-size: 14px;
                margin: 0;
            }

            /* ─── Responsive ──────────────────────────────────────────────────── */
            @media (max-width: 1200px) {
                .desktop-shc-grid { grid-template-columns: repeat(2, 1fr); }
            }
            @media (max-width: 768px) {
                #desktop-shc-root { padding: 12px; }
                .desktop-shc-grid { grid-template-columns: 1fr; }
                .desktop-shc-top-bar { flex-direction: column; align-items: stretch; }
                .desktop-shc-controls { flex-wrap: wrap; }
                .desktop-shc-search-wrapper input { min-width: 100%; }
                .desktop-shc-stats { grid-template-columns: 1fr 1fr; }
            }
            @media (max-width: 480px) {
                .desktop-shc-stats { grid-template-columns: 1fr; }
            }
        </style>
    `;

    // ─── Inject HTML ──────────────────────────────────────────────────────────
    $(page.main).append(html);

    // ─── Initialize ──────────────────────────────────────────────────────────
    const root = document.getElementById('desktop-shc-root');
    root.dataset.theme = currentTheme;

    // ─── Helper: Open in new tab ────────────────────────────────────────────
    function openInNewTab(url) {
        const win = window.open(url, '_blank');
        if (win) { win.focus(); }
        else { window.location.href = url; }
    }

    // ─── Get URL for different types ──────────────────────────────────────────
    function getRoute(type, name) {
        if (type === 'List') {
            return `/app/list/${name}`;
        } else if (type === 'Report') {
            return `/app/query-report/${name}`;
        } else {
            return `/app/${name}`;
        }
    }

    // ─── Open Desktop Item ──────────────────────────────────────────────────
    window.openDesktopItem = function(type, name) {
        const url = getRoute(type, name);
        openInNewTab(url);
    };

    // ─── Toggle Favorite ────────────────────────────────────────────────────
    window.toggleFavorite = function(id) {
        let favorites = JSON.parse(localStorage.getItem('desktop_shc_favorites') || '[]');
        const index = favorites.indexOf(id);
        if (index > -1) {
            favorites.splice(index, 1);
        } else {
            favorites.push(id);
        }
        localStorage.setItem('desktop_shc_favorites', JSON.stringify(favorites));

        // Update all favorited items
        document.querySelectorAll('.fav-btn').forEach(btn => {
            const name = btn.closest('.desktop-shc-item').dataset.name;
            if (favorites.includes(name)) {
                btn.textContent = '⭐';
                btn.classList.add('active');
            } else {
                btn.textContent = '☆';
                btn.classList.remove('active');
            }
        });

        updateStats();
    };

    // ─── Update Stats ───────────────────────────────────────────────────────
    function updateStats() {
        const favorites = JSON.parse(localStorage.getItem('desktop_shc_favorites') || '[]');
        document.getElementById('favorite-count').textContent = favorites.length;
    }

    // ─── Search Filter ──────────────────────────────────────────────────────
    function applyFilter(filter) {
        const items = document.querySelectorAll('.desktop-shc-item');
        const groups = document.querySelectorAll('.desktop-shc-group');
        const empty = document.getElementById('desktop-shc-empty');
        let visibleCount = 0;

        const searchLower = filter.toLowerCase().trim();

        groups.forEach(group => {
            let groupHasVisible = false;
            const groupItems = group.querySelectorAll('.desktop-shc-item');

            groupItems.forEach(item => {
                const name = item.dataset.name.toLowerCase();
                const isVisible = !searchLower || name.includes(searchLower);
                item.style.display = isVisible ? 'flex' : 'none';
                if (isVisible) {
                    groupHasVisible = true;
                    visibleCount++;
                }
            });

            group.style.display = groupHasVisible ? 'flex' : 'none';
        });

        empty.style.display = visibleCount === 0 ? 'block' : 'none';
    }

    // ─── Theme Switching ────────────────────────────────────────────────────
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const theme = this.dataset.theme;
            root.dataset.theme = theme;
            localStorage.setItem('desktop_shc_theme', theme);
            document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentTheme = theme;
        });
    });

    // ─── Search ─────────────────────────────────────────────────────────────
    document.getElementById('desktop-shc-search').addEventListener('input', function() {
        applyFilter(this.value);
    });

    // ─── Keyboard Shortcuts ──────────────────────────────────────────────────
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('desktop-shc-search').focus();
        }
        if (e.key === 'Escape') {
            document.getElementById('desktop-shc-search').blur();
        }
    });

    // ─── Initialize Favorites ──────────────────────────────────────────────
    const favorites = JSON.parse(localStorage.getItem('desktop_shc_favorites') || '[]');
    document.querySelectorAll('.fav-btn').forEach(btn => {
        const name = btn.closest('.desktop-shc-item').dataset.name;
        if (favorites.includes(name)) {
            btn.textContent = '⭐';
            btn.classList.add('active');
        }
    });

    // ─── Initial Render ─────────────────────────────────────────────────────
    updateStats();

    // ─── Expose for debugging ──────────────────────────────────────────────
    window.desktopShc = {
        GROUPS,
        openDesktopItem,
        toggleFavorite,
        applyFilter
    };
};