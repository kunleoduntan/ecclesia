// broker/broker/page/ecclesia/ecclesia.js
// Ecclesia — Central Command Center v2
// Sectional grouping with professional presentation

frappe.pages['ecclesia'] = frappe.pages['ecclesia'] || {};

frappe.pages['ecclesia'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '🏛️ Ecclesia',
        single_column: true
    });

    // ─── Themes ──────────────────────────────────────────────────────────────
    const THEMES = {
        corporate: {
            name: 'Corporate',
            primary: '#1E293B',
            secondary: '#475569',
            accent: '#3B82F6',
            bg: '#F8FAFC',
            card: '#FFFFFF',
            text: '#0F172A',
            textMuted: '#64748B',
            border: '#E2E8F0',
            gradient: 'linear-gradient(135deg,#1E293B 0%,#3B82F6 100%)',
            sectionBg: 'rgba(59,130,246,0.04)'
        },
        emerald: {
            name: 'Emerald',
            primary: '#065F46',
            secondary: '#059669',
            accent: '#34D399',
            bg: '#ECFDF5',
            card: '#FFFFFF',
            text: '#022C22',
            textMuted: '#047857',
            border: '#A7F3D0',
            gradient: 'linear-gradient(135deg,#022C22 0%,#059669 50%,#34D399 100%)',
            sectionBg: 'rgba(5,150,105,0.06)'
        },
        royal: {
            name: 'Royal',
            primary: '#4C1D95',
            secondary: '#7C3AED',
            accent: '#A78BFA',
            bg: '#FAF5FF',
            card: '#FFFFFF',
            text: '#2E1065',
            textMuted: '#6D28D9',
            border: '#E9D5FF',
            gradient: 'linear-gradient(135deg,#1E1B4B 0%,#7C3AED 50%,#A78BFA 100%)',
            sectionBg: 'rgba(124,58,237,0.06)'
        },
        sunset: {
            name: 'Sunset',
            primary: '#9A3412',
            secondary: '#EA580C',
            accent: '#F97316',
            bg: '#FFF7ED',
            card: '#FFFFFF',
            text: '#431407',
            textMuted: '#9A3412',
            border: '#FED7AA',
            gradient: 'linear-gradient(135deg,#431407 0%,#EA580C 50%,#FBBF24 100%)',
            sectionBg: 'rgba(234,88,12,0.06)'
        },
        ocean: {
            name: 'Ocean',
            primary: '#0C4A6E',
            secondary: '#0284C7',
            accent: '#38BDF8',
            bg: '#F0F9FF',
            card: '#FFFFFF',
            text: '#0C4A6E',
            textMuted: '#0369A1',
            border: '#BAE6FD',
            gradient: 'linear-gradient(135deg,#0C4A6E 0%,#0284C7 50%,#38BDF8 100%)',
            sectionBg: 'rgba(2,132,199,0.06)'
        },
        midnight: {
            name: 'Midnight',
            primary: '#0F172A',
            secondary: '#1E293B',
            accent: '#818CF8',
            bg: '#0F172A',
            card: '#1E293B',
            text: '#F1F5F9',
            textMuted: '#94A3B8',
            border: '#334155',
            gradient: 'linear-gradient(135deg,#020617 0%,#1E293B 50%,#6366F1 100%)',
            sectionBg: 'rgba(99,102,241,0.08)'
        },
        forest: {
            name: 'Forest',
            primary: '#052E16',
            secondary: '#166534',
            accent: '#22C55E',
            bg: '#052E16',
            card: '#14532D',
            text: '#F0FDF4',
            textMuted: '#86EFAC',
            border: '#166534',
            gradient: 'linear-gradient(135deg,#052E16 0%,#166534 50%,#22C55E 100%)',
            sectionBg: 'rgba(34,197,94,0.08)'
        }
    };

    // ─── Get saved theme ────────────────────────────────────────────────────
    const savedTheme = localStorage.getItem('ecclesia-theme') || 'corporate';
    let currentTheme = savedTheme;

    // ─── Tabs ────────────────────────────────────────────────────────────────
    const TABS = [
        { id: 'doctypes', label: '📋 Doctypes', icon: '📋' },
        { id: 'dashboards', label: '📊 Dashboards', icon: '📊' },
        { id: 'favorites', label: '⭐ Favorites', icon: '⭐' },
        { id: 'presentation', label: '📽️ Presentation', icon: '📽️' }
    ];

    // ─── Doctype Categories with icons ─────────────────────────────────────
    const DOCTYPE_CATEGORIES = {
        'Compliance': { icon: '📜', color: '#8B5CF6', order: 1 },
        'Regulatory': { icon: '🏛️', color: '#DC2626', order: 2 },
        'AML & KYC': { icon: '🛡️', color: '#059669', order: 3 },
        'HR & Employee': { icon: '👤', color: '#6366F1', order: 4 },
        'Performance': { icon: '⭐', color: '#F59E0B', order: 5 },
        'CRM': { icon: '🤝', color: '#3B82F6', order: 6 },
        'Pensions': { icon: '🏦', color: '#0D9488', order: 7 },
        'Assets': { icon: '🏗️', color: '#8B5CF6', order: 8 },
        'Facility': { icon: '🔧', color: '#F97316', order: 9 },
        'Security': { icon: '🔒', color: '#EF4444', order: 10 },
        'Finance': { icon: '💰', color: '#059669', order: 11 },
        'Audit': { icon: '🔍', color: '#F43F5E', order: 12 },
        'System': { icon: '⚙️', color: '#475569', order: 13 },
        'WhatsApp': { icon: '💬', color: '#25D366', order: 14 },
        'Workflow': { icon: '🔄', color: '#F59E0B', order: 15 },
        'Other': { icon: '📁', color: '#6B7280', order: 16 }
    };

    // ─── Doctype Shortcuts ──────────────────────────────────────────────────
    const DOCTYPES = [
        // Compliance
        { name: 'Compliance Policy', icon: '📜', color: '#8B5CF6', category: 'Compliance' },
        { name: 'Compliance Rule', icon: '⚖️', color: '#7C3AED', category: 'Compliance' },
        { name: 'Compliance Period', icon: '📅', color: '#6D28D9', category: 'Compliance' },
        { name: 'Compliance Alert Rule', icon: '🔔', color: '#F59E0B', category: 'Compliance' },
        { name: 'Compliance Event Log', icon: '📋', color: '#D97706', category: 'Compliance' },
        { name: 'Compliance KPI Snapshot', icon: '📊', color: '#059669', category: 'Compliance' },
        { name: 'Compliance Payment Allocation', icon: '💰', color: '#10B981', category: 'Compliance' },
        { name: 'Compliance Liability Ledger', icon: '📒', color: '#6366F1', category: 'Compliance' },
        { name: 'Compliance Calendar', icon: '🗓️', color: '#EC4899', category: 'Compliance' },
        { name: 'Compliance Audit', icon: '🔍', color: '#F43F5E', category: 'Compliance' },
        { name: 'Compliance Incident', icon: '🚨', color: '#EF4444', category: 'Compliance' },
        { name: 'Compliance Risk Register', icon: '⚠️', color: '#F97316', category: 'Compliance' },
        { name: 'Compliance Exception', icon: '❌', color: '#DC2626', category: 'Compliance' },
        { name: 'Compliance Task', icon: '✅', color: '#22C55E', category: 'Compliance' },
        { name: 'Compliance Register', icon: '📇', color: '#8B5CF6', category: 'Compliance' },
        { name: 'Compliance Filing', icon: '📄', color: '#3B82F6', category: 'Compliance' },
        { name: 'Compliance Training Record', icon: '🎓', color: '#8B5CF6', category: 'Compliance' },
        { name: 'Compliance Training Calendar', icon: '📆', color: '#A78BFA', category: 'Compliance' },
        { name: 'Corporate Compliance Register', icon: '🏢', color: '#1E3A5F', category: 'Compliance' },
        // Regulatory
        { name: 'Regulatory Authority', icon: '🏛️', color: '#DC2626', category: 'Regulatory' },
        { name: 'Regulatory Return', icon: '📤', color: '#EA580C', category: 'Regulatory' },
        { name: 'Statutory Register Entry', icon: '📚', color: '#D97706', category: 'Regulatory' },
        { name: 'Board Resolution', icon: '📜', color: '#7C3AED', category: 'Regulatory' },
        { name: 'Whistleblower Report', icon: '🔊', color: '#EF4444', category: 'Regulatory' },
        // AML & KYC
        { name: 'AML KYC Record', icon: '🛡️', color: '#059669', category: 'AML & KYC' },
        { name: 'Suspicious Transaction Report', icon: '🚩', color: '#DC2626', category: 'AML & KYC' },
        { name: 'Conflict of Interest Declaration', icon: '⚖️', color: '#F59E0B', category: 'AML & KYC' },
        // HR & Employee
        { name: 'Employee Loan Type', icon: '💰', color: '#10B981', category: 'HR & Employee' },
        { name: 'Employee Loan Application', icon: '📋', color: '#059669', category: 'HR & Employee' },
        { name: 'Loan Repayment Entry', icon: '💳', color: '#0284C7', category: 'HR & Employee' },
        { name: 'Staff Loan Payment', icon: '💵', color: '#16A34A', category: 'HR & Employee' },
        { name: 'Employee Document', icon: '📁', color: '#6366F1', category: 'HR & Employee' },
        { name: 'Employee Performance Record', icon: '⭐', color: '#F59E0B', category: 'HR & Employee' },
        { name: 'Employee Tax Computation', icon: '🧾', color: '#DC2626', category: 'HR & Employee' },
        // Performance
        { name: 'Performance Cycle', icon: '🔄', color: '#8B5CF6', category: 'Performance' },
        { name: 'Manager Review', icon: '👔', color: '#1E293B', category: 'Performance' },
        { name: 'Calibration Session', icon: '⚙️', color: '#0284C7', category: 'Performance' },
        { name: 'Peer Review Request', icon: '🤝', color: '#22C55E', category: 'Performance' },
        { name: 'KPI Library', icon: '📊', color: '#F59E0B', category: 'Performance' },
        // CRM
        { name: 'CRM Deal Stage', icon: '📈', color: '#8B5CF6', category: 'CRM' },
        { name: 'CRM Source', icon: '🔗', color: '#3B82F6', category: 'CRM' },
        { name: 'CRM Activity', icon: '📝', color: '#10B981', category: 'CRM' },
        { name: 'CRM Contact', icon: '👤', color: '#0284C7', category: 'CRM' },
        { name: 'CRM Account', icon: '🏢', color: '#6366F1', category: 'CRM' },
        { name: 'CRM Pipeline', icon: '🔀', color: '#8B5CF6', category: 'CRM' },
        { name: 'CRM Meeting', icon: '📅', color: '#F59E0B', category: 'CRM' },
        { name: 'CRM Quota Target', icon: '🎯', color: '#EF4444', category: 'CRM' },
        { name: 'CRM Territory', icon: '🌍', color: '#10B981', category: 'CRM' },
        { name: 'CRM Deal', icon: '🤝', color: '#7C3AED', category: 'CRM' },
        { name: 'CRM Lead', icon: '🔹', color: '#3B82F6', category: 'CRM' },
        { name: 'CRM Opportunity', icon: '💎', color: '#F59E0B', category: 'CRM' },
        // Pensions
        { name: 'Pension Remittance Batch', icon: '🏦', color: '#059669', category: 'Pensions' },
        { name: 'Pension Manager', icon: '👤', color: '#0D9488', category: 'Pensions' },
        { name: 'NHF Remittance Batch', icon: '🏠', color: '#D97706', category: 'Pensions' },
        { name: 'HMO Manager', icon: '🏥', color: '#DC2626', category: 'Pensions' },
        // Assets
        { name: 'Fixed Asset', icon: '🏗️', color: '#6366F1', category: 'Assets' },
        { name: 'Fixed Asset Category', icon: '📂', color: '#8B5CF6', category: 'Assets' },
        { name: 'Fixed Asset Purchase', icon: '🛒', color: '#059669', category: 'Assets' },
        { name: 'Fixed Asset Transfer', icon: '🔄', color: '#F59E0B', category: 'Assets' },
        { name: 'Fixed Asset Revaluation', icon: '📈', color: '#0284C7', category: 'Assets' },
        { name: 'Fixed Asset Insurance', icon: '🛡️', color: '#7C3AED', category: 'Assets' },
        { name: 'Fixed Asset Maintenance', icon: '🔧', color: '#F97316', category: 'Assets' },
        { name: 'Fixed Asset Lease', icon: '📋', color: '#10B981', category: 'Assets' },
        { name: 'Fixed Asset Verification', icon: '✅', color: '#22C55E', category: 'Assets' },
        { name: 'Fixed Asset Disposal', icon: '🗑️', color: '#EF4444', category: 'Assets' },
        { name: 'Fixed Asset Depreciation Entry', icon: '📉', color: '#6B7280', category: 'Assets' },
        // Facility
        { name: 'Facility', icon: '🏭', color: '#6366F1', category: 'Facility' },
        { name: 'Facility Maintenance Request', icon: '🔧', color: '#F97316', category: 'Facility' },
        { name: 'Maintenance Work Order', icon: '📋', color: '#F59E0B', category: 'Facility' },
        { name: 'Generator Log', icon: '⚡', color: '#DC2626', category: 'Facility' },
        { name: 'Fuel Issue', icon: '⛽', color: '#F97316', category: 'Facility' },
        { name: 'Utility Consumption', icon: '💡', color: '#059669', category: 'Facility' },
        { name: 'Utility Meter', icon: '📊', color: '#0284C7', category: 'Facility' },
        { name: 'Service Provider', icon: '🔧', color: '#8B5CF6', category: 'Facility' },
        // Security
        { name: 'Security Incident', icon: '🚨', color: '#EF4444', category: 'Security' },
        { name: 'Visitor Register', icon: '📕', color: '#6B7280', category: 'Security' },
        { name: 'HSE Inspection', icon: '🔬', color: '#059669', category: 'Security' },
        { name: 'Data Breach Register', icon: '🔓', color: '#DC2626', category: 'Security' },
        // Finance
        { name: 'Bank Reconciliation', icon: '🏦', color: '#059669', category: 'Finance' },
        { name: 'Bank Reconciliation Statement', icon: '📊', color: '#10B981', category: 'Finance' },
        { name: 'Bank Statement Upload', icon: '📤', color: '#0284C7', category: 'Finance' },
        { name: 'Bank Transaction Processor', icon: '⚙️', color: '#4B5563', category: 'Finance' },
        { name: 'Payment Batch', icon: '💳', color: '#059669', category: 'Finance' },
        { name: 'Payments', icon: '💵', color: '#10B981', category: 'Finance' },
        { name: 'Receipts', icon: '🧾', color: '#0284C7', category: 'Finance' },
        { name: 'Journal Entry Voucher', icon: '🧾', color: '#8B5CF6', category: 'Finance' },
        // Audit
        { name: 'Audit Universe', icon: '🌌', color: '#8B5CF6', category: 'Audit' },
        { name: 'Annual Audit Plan', icon: '📅', color: '#7C3AED', category: 'Audit' },
        { name: 'Audit Engagement', icon: '🤝', color: '#6D28D9', category: 'Audit' },
        { name: 'Audit Checklist', icon: '✅', color: '#4C1D95', category: 'Audit' },
        { name: 'Audit Finding', icon: '🔍', color: '#EF4444', category: 'Audit' },
        { name: 'Audit Report', icon: '📄', color: '#DC2626', category: 'Audit' },
        // System
        { name: 'Audit Trail Settings', icon: '🔒', color: '#1E293B', category: 'System' },
        { name: 'System Integrity Log', icon: '📊', color: '#4B5563', category: 'System' },
        { name: 'Doctype Creator', icon: '🛠️', color: '#8B5CF6', category: 'System' },
        // WhatsApp
        { name: 'WA Settings', icon: '⚙️', color: '#25D366', category: 'WhatsApp' },
        { name: 'WA Template', icon: '📝', color: '#128C7E', category: 'WhatsApp' },
        { name: 'WA Quick Reply', icon: '💬', color: '#075E54', category: 'WhatsApp' },
        { name: 'WA Message', icon: '📨', color: '#128C7E', category: 'WhatsApp' },
        { name: 'WA Broadcast', icon: '📢', color: '#25D366', category: 'WhatsApp' },
        // Workflow
        { name: 'Work Session', icon: '💻', color: '#059669', category: 'Workflow' },
        { name: 'WFH Schedule', icon: '🏠', color: '#F59E0B', category: 'Workflow' },
        { name: 'WFH Session', icon: '🖥️', color: '#D97706', category: 'Workflow' },
        { name: 'WFH Request', icon: '📋', color: '#F97316', category: 'Workflow' },
        { name: 'Work Activity Log', icon: '📝', color: '#6B7280', category: 'Workflow' },
        // Other
        { name: 'Communique', icon: '📢', color: '#8B5CF6', category: 'Other' },
        { name: 'Social Post', icon: '📱', color: '#EC4899', category: 'Other' },
        { name: 'Meeting Room Booking', icon: '🏢', color: '#8B5CF6', category: 'Other' },
        { name: 'Vehicle Request', icon: '🚗', color: '#F59E0B', category: 'Other' },
        { name: 'eRequest', icon: '📨', color: '#6366F1', category: 'Other' },
        { name: 'Ecclesia Investment', icon: '📈', color: '#059669', category: 'Other' }
    ];

    // ─── Dashboard Categories ──────────────────────────────────────────────
    const DASHBOARD_CATEGORIES = {
        'Command Centers': { icon: '🏛️', color: '#8B5CF6', order: 1 },
        'Compliance': { icon: '📜', color: '#7C3AED', order: 2 },
        'Finance & Banking': { icon: '💰', color: '#059669', order: 3 },
        'CRM & Sales': { icon: '🤝', color: '#3B82F6', order: 4 },
        'Social Media': { icon: '📱', color: '#EC4899', order: 5 },
        'Workplace & WFH': { icon: '🏠', color: '#F59E0B', order: 6 },
        'Audit & Compliance': { icon: '🔍', color: '#F43F5E', order: 7 },
        'Operations': { icon: '⚙️', color: '#475569', order: 8 },
        'Design & Build': { icon: '🛠️', color: '#D97706', order: 9 },
        'System & Admin': { icon: '🔒', color: '#1E293B', order: 10 }
    };

    // ─── Dashboards ──────────────────────────────────────────────────────────
    const DASHBOARDS = [
        // Command Centers
        { id: 'ecclesia', name: 'Ecclesia', icon: '🏛️', color: '#8B5CF6', desc: 'Central command center', category: 'Command Centers' },
        { id: 'compliance-hq', name: 'Compliance HQ', icon: '🏢', color: '#4C1D95', desc: 'Headquarters view', category: 'Command Centers' },
        { id: 'admhq', name: 'ADM HQ', icon: '⚙️', color: '#1E293B', desc: 'Admin headquarters', category: 'Command Centers' },
        { id: 'wfh-command-center', name: 'WFH Command Center', icon: '🏠', color: '#F59E0B', desc: 'Remote work control', category: 'Command Centers' },
        // Compliance
        { id: 'compliance-shelf', name: 'Compliance Shelf', icon: '📚', color: '#7C3AED', desc: 'Compliance library', category: 'Compliance' },
        { id: 'compliance-hub', name: 'Compliance Hub', icon: '🎯', color: '#6D28D9', desc: 'Compliance operations', category: 'Compliance' },
        { id: 'compliance-dashboard', name: 'Compliance Dashboard', icon: '📊', color: '#5B21B6', desc: 'Compliance metrics', category: 'Compliance' },
        // Finance & Banking
        { id: 'bank-reconciliation-studio', name: 'Bank Recon Studio', icon: '🏦', color: '#059669', desc: 'Reconciliation workspace', category: 'Finance & Banking' },
        { id: 'ap-ar-check', name: 'AP/AR Check', icon: '✅', color: '#10B981', desc: 'Payables & receivables', category: 'Finance & Banking' },
        { id: 'banking', name: 'Banking', icon: '💳', color: '#0284C7', desc: 'Banking operations', category: 'Finance & Banking' },
        { id: 'gl-analytical-review', name: 'GL Analytical Review', icon: '📊', color: '#10B981', desc: 'Ledger analysis', category: 'Finance & Banking' },
        // CRM & Sales
        { id: 'crms-dashboard', name: 'CRMS Dashboard', icon: '🤝', color: '#8B5CF6', desc: 'CRM system view', category: 'CRM & Sales' },
        { id: 'crm-dashboard', name: 'CRM Dashboard', icon: '📈', color: '#7C3AED', desc: 'Sales pipeline', category: 'CRM & Sales' },
        { id: 'sales-funnel', name: 'Sales Funnel', icon: '📈', color: '#F59E0B', desc: 'Sales pipeline view', category: 'CRM & Sales' },
        // Social Media
        { id: 'smm-virtual', name: 'SMM Virtual', icon: '📱', color: '#EC4899', desc: 'Social media management', category: 'Social Media' },
        { id: 'smm-dashboard', name: 'SMM Dashboard', icon: '📊', color: '#F472B6', desc: 'Social media metrics', category: 'Social Media' },
        { id: 'social-media-dashboard', name: 'Social Media Dashboard', icon: '📱', color: '#EC4899', desc: 'Social analytics', category: 'Social Media' },
        // Workplace & WFH
        { id: 'live-dashboard', name: 'Live Dashboard', icon: '🔴', color: '#EF4444', desc: 'Real-time metrics', category: 'Workplace & WFH' },
        { id: 'wfh-dashboard', name: 'WFH Dashboard', icon: '💻', color: '#D97706', desc: 'WFH analytics', category: 'Workplace & WFH' },
        { id: 'team-updates', name: 'Team Updates', icon: '💬', color: '#22C55E', desc: 'Team communication', category: 'Workplace & WFH' },
        // Audit & Compliance
        { id: 'audit-dashboard', name: 'Audit Dashboard', icon: '🔍', color: '#F43F5E', desc: 'Audit overview', category: 'Audit & Compliance' },
        // Operations
        { id: 'stock-recon', name: 'Stock Recon', icon: '📦', color: '#059669', desc: 'Inventory reconciliation', category: 'Operations' },
        { id: 'stock-balance', name: 'Stock Balance', icon: '📦', color: '#10B981', desc: 'Inventory status', category: 'Operations' },
        { id: 'warehouse-capacity-summary', name: 'Warehouse Summary', icon: '🏗️', color: '#0284C7', desc: 'Storage capacity', category: 'Operations' },
        { id: 'visual-plant-floor', name: 'Visual Plant Floor', icon: '🏭', color: '#059669', desc: 'Factory visualization', category: 'Operations' },
        { id: 'point-of-sale', name: 'Point of Sale', icon: '🛒', color: '#059669', desc: 'Sales terminal', category: 'Operations' },
        { id: 'ecc-pos', name: 'ECC POS', icon: '🖥️', color: '#6366F1', desc: 'Point of sale', category: 'Operations' },
        // Design & Build
        { id: 'workflow-builder', name: 'Workflow Builder', icon: '🔧', color: '#F97316', desc: 'Process design', category: 'Design & Build' },
        { id: 'print-format-builder-beta', name: 'Print Format Builder β', icon: '🖨️', color: '#D97706', desc: 'PDF design tool', category: 'Design & Build' },
        { id: 'print-format-builder', name: 'Print Format Builder', icon: '🖨️', color: '#D97706', desc: 'PDF template design', category: 'Design & Build' },
        { id: 'bom-comparison-tool', name: 'BOM Comparison', icon: '📋', color: '#F59E0B', desc: 'Bill of materials compare', category: 'Design & Build' },
        // System & Admin
        { id: 'admin-dashboard', name: 'Admin Dashboard', icon: '🖥️', color: '#475569', desc: 'Administration overview', category: 'System & Admin' },
        { id: 'desktop', name: 'Desktop', icon: '🖥️', color: '#6B7280', desc: 'Workspace desktop', category: 'System & Admin' },
        { id: 'dashboard-view', name: 'Dashboard View', icon: '📊', color: '#8B5CF6', desc: 'Custom dashboards', category: 'System & Admin' },
        { id: 'organizational-chart', name: 'Org Chart', icon: '👥', color: '#7C3AED', desc: 'Company structure', category: 'System & Admin' },
        { id: 'permission-manager', name: 'Permission Manager', icon: '🔒', color: '#DC2626', desc: 'Access control', category: 'System & Admin' },
        { id: 'setup-wizard', name: 'Setup Wizard', icon: '⚙️', color: '#1E293B', desc: 'Initial configuration', category: 'System & Admin' },
        // Utilities
        { id: 'data-wipe-utility', name: 'Data Wipe Utility', icon: '🗑️', color: '#DC2626', desc: 'Data cleaning tool', category: 'System & Admin' },
        { id: 'bulk-importer', name: 'Bulk Importer', icon: '📥', color: '#8B5CF6', desc: 'Mass data import', category: 'System & Admin' },
        { id: 'mail_hub', name: 'Mail Hub', icon: '📧', color: '#3B82F6', desc: 'Email management', category: 'System & Admin' },
        { id: 'backups', name: 'Backups', icon: '💾', color: '#6B7280', desc: 'Data backups', category: 'System & Admin' },
        { id: 'print', name: 'Print Center', icon: '🖨️', color: '#4B5563', desc: 'Print management', category: 'System & Admin' }
    ];

    // ─── Build HTML ──────────────────────────────────────────────────────────
    const html = `
        <div id="ecclesia-root">
            <!-- Top Bar -->
            <div class="ecclesia-top-bar">
                <div class="ecclesia-brand">
                    <span class="brand-icon">🏛️</span>
                    <span class="brand-name">Ecclesia</span>
                    <span class="brand-version">v2.0</span>
                </div>
                <div class="ecclesia-controls">
                    <div class="ecclesia-theme-selector">
                        ${Object.entries(THEMES).map(([key, t]) => `
                            <button class="theme-btn ${key === currentTheme ? 'active' : ''}" 
                                    data-theme="${key}" title="${t.name}"
                                    style="background: ${t.primary};">
                                <span class="theme-dot" style="background: ${t.accent};"></span>
                            </button>
                        `).join('')}
                    </div>
                    <div class="ecclesia-search-wrapper">
                        <input type="text" id="ecclesia-search" placeholder="Search doctypes, dashboards..." />
                        <span class="search-shortcut">⌘K</span>
                    </div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="ecclesia-tabs">
                ${TABS.map(tab => `
                    <button class="ecclesia-tab ${tab.id === 'doctypes' ? 'active' : ''}" data-tab="${tab.id}">
                        ${tab.label}
                    </button>
                `).join('')}
            </div>

            <!-- Content -->
            <div class="ecclesia-content">
                <!-- Doctypes Tab -->
                <div class="ecclesia-panel active" data-panel="doctypes">
                    <div class="ecclesia-stats">
                        <div class="stat-card">
                            <span class="stat-icon">📋</span>
                            <span class="stat-number">${DOCTYPES.length}</span>
                            <span class="stat-label">Doctypes</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-icon">📂</span>
                            <span class="stat-number">${Object.keys(DOCTYPE_CATEGORIES).length}</span>
                            <span class="stat-label">Categories</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-icon">⭐</span>
                            <span class="stat-number" id="favorite-count">0</span>
                            <span class="stat-label">Favorites</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-icon">🔗</span>
                            <span class="stat-number">${DASHBOARDS.length}</span>
                            <span class="stat-label">Dashboards</span>
                        </div>
                    </div>
                    <div id="doctype-sections"></div>
                </div>

                <!-- Dashboards Tab -->
                <div class="ecclesia-panel" data-panel="dashboards">
                    <div class="ecclesia-stats">
                        <div class="stat-card">
                            <span class="stat-icon">📊</span>
                            <span class="stat-number">${DASHBOARDS.length}</span>
                            <span class="stat-label">Dashboards</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-icon">📂</span>
                            <span class="stat-number">${Object.keys(DASHBOARD_CATEGORIES).length}</span>
                            <span class="stat-label">Categories</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-icon">🚀</span>
                            <span class="stat-number">${DASHBOARDS.filter(d => d.category === 'Command Centers').length}</span>
                            <span class="stat-label">Command Centers</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-icon">⚡</span>
                            <span class="stat-number">${DASHBOARDS.filter(d => d.category === 'System & Admin').length}</span>
                            <span class="stat-label">Admin Tools</span>
                        </div>
                    </div>
                    <div id="dashboard-sections"></div>
                </div>

                <!-- Favorites Tab -->
                <div class="ecclesia-panel" data-panel="favorites">
                    <div class="ecclesia-stats">
                        <div class="stat-card">
                            <span class="stat-icon">⭐</span>
                            <span class="stat-number" id="fav-doctype-count">0</span>
                            <span class="stat-label">Doctypes</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-icon">📊</span>
                            <span class="stat-number" id="fav-dashboard-count">0</span>
                            <span class="stat-label">Dashboards</span>
                        </div>
                    </div>
                    <div id="favorites-container"></div>
                </div>

                <!-- Presentation Tab -->
                <div class="ecclesia-panel" data-panel="presentation">
                    <div class="presentation-grid" id="presentation-grid">
                        <!-- Dynamically rendered -->
                    </div>
                </div>
            </div>
        </div>

        <style>
            /* ─── Base ─────────────────────────────────────────────────────────── */
            #ecclesia-root {
                padding: 16px 20px;
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background: var(--ecclesia-bg, #F8FAFC);
                color: var(--ecclesia-text, #0F172A);
                min-height: 100vh;
                transition: all 0.3s ease;
            }

            /* ─── Theme Variables ────────────────────────────────────────────── */
            #ecclesia-root[data-theme="corporate"] {
                --ecclesia-primary: #1E293B; --ecclesia-secondary: #475569;
                --ecclesia-accent: #3B82F6; --ecclesia-bg: #F8FAFC;
                --ecclesia-card: #FFFFFF; --ecclesia-text: #0F172A;
                --ecclesia-muted: #64748B; --ecclesia-border: #E2E8F0;
                --ecclesia-gradient: linear-gradient(135deg,#1E293B 0%,#3B82F6 100%);
                --ecclesia-section-bg: rgba(59,130,246,0.04);
            }
            #ecclesia-root[data-theme="emerald"] {
                --ecclesia-primary: #065F46; --ecclesia-secondary: #059669;
                --ecclesia-accent: #34D399; --ecclesia-bg: #ECFDF5;
                --ecclesia-card: #FFFFFF; --ecclesia-text: #022C22;
                --ecclesia-muted: #047857; --ecclesia-border: #A7F3D0;
                --ecclesia-gradient: linear-gradient(135deg,#022C22 0%,#059669 50%,#34D399 100%);
                --ecclesia-section-bg: rgba(5,150,105,0.06);
            }
            #ecclesia-root[data-theme="royal"] {
                --ecclesia-primary: #4C1D95; --ecclesia-secondary: #7C3AED;
                --ecclesia-accent: #A78BFA; --ecclesia-bg: #FAF5FF;
                --ecclesia-card: #FFFFFF; --ecclesia-text: #2E1065;
                --ecclesia-muted: #6D28D9; --ecclesia-border: #E9D5FF;
                --ecclesia-gradient: linear-gradient(135deg,#1E1B4B 0%,#7C3AED 50%,#A78BFA 100%);
                --ecclesia-section-bg: rgba(124,58,237,0.06);
            }
            #ecclesia-root[data-theme="sunset"] {
                --ecclesia-primary: #9A3412; --ecclesia-secondary: #EA580C;
                --ecclesia-accent: #F97316; --ecclesia-bg: #FFF7ED;
                --ecclesia-card: #FFFFFF; --ecclesia-text: #431407;
                --ecclesia-muted: #9A3412; --ecclesia-border: #FED7AA;
                --ecclesia-gradient: linear-gradient(135deg,#431407 0%,#EA580C 50%,#FBBF24 100%);
                --ecclesia-section-bg: rgba(234,88,12,0.06);
            }
            #ecclesia-root[data-theme="ocean"] {
                --ecclesia-primary: #0C4A6E; --ecclesia-secondary: #0284C7;
                --ecclesia-accent: #38BDF8; --ecclesia-bg: #F0F9FF;
                --ecclesia-card: #FFFFFF; --ecclesia-text: #0C4A6E;
                --ecclesia-muted: #0369A1; --ecclesia-border: #BAE6FD;
                --ecclesia-gradient: linear-gradient(135deg,#0C4A6E 0%,#0284C7 50%,#38BDF8 100%);
                --ecclesia-section-bg: rgba(2,132,199,0.06);
            }
            #ecclesia-root[data-theme="midnight"] {
                --ecclesia-primary: #0F172A; --ecclesia-secondary: #1E293B;
                --ecclesia-accent: #818CF8; --ecclesia-bg: #0F172A;
                --ecclesia-card: #1E293B; --ecclesia-text: #F1F5F9;
                --ecclesia-muted: #94A3B8; --ecclesia-border: #334155;
                --ecclesia-gradient: linear-gradient(135deg,#020617 0%,#1E293B 50%,#6366F1 100%);
                --ecclesia-section-bg: rgba(99,102,241,0.08);
            }
            #ecclesia-root[data-theme="forest"] {
                --ecclesia-primary: #052E16; --ecclesia-secondary: #166534;
                --ecclesia-accent: #22C55E; --ecclesia-bg: #052E16;
                --ecclesia-card: #14532D; --ecclesia-text: #F0FDF4;
                --ecclesia-muted: #86EFAC; --ecclesia-border: #166534;
                --ecclesia-gradient: linear-gradient(135deg,#052E16 0%,#166534 50%,#22C55E 100%);
                --ecclesia-section-bg: rgba(34,197,94,0.08);
            }

            /* ─── Top Bar ──────────────────────────────────────────────────────── */
            .ecclesia-top-bar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 20px;
                flex-wrap: wrap;
                background: var(--ecclesia-card);
                padding: 12px 20px;
                border-radius: 16px;
                border: 1px solid var(--ecclesia-border);
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }
            .ecclesia-brand {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .brand-icon { font-size: 24px; }
            .brand-name {
                font-size: 18px;
                font-weight: 800;
                color: var(--ecclesia-text);
            }
            .brand-version {
                font-size: 10px;
                font-weight: 600;
                color: var(--ecclesia-muted);
                background: var(--ecclesia-bg);
                padding: 2px 8px;
                border-radius: 12px;
            }
            .ecclesia-controls {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }
            .ecclesia-theme-selector {
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
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
            }
            .theme-btn:hover { transform: scale(1.1); }
            .theme-btn.active {
                border-color: var(--ecclesia-accent);
                box-shadow: 0 0 0 3px var(--ecclesia-accent)33;
            }
            .theme-dot { width: 14px; height: 14px; border-radius: 50%; display: block; }
            .ecclesia-search-wrapper {
                position: relative;
                display: flex;
                align-items: center;
            }
            .ecclesia-search-wrapper input {
                padding: 8px 16px;
                padding-right: 60px;
                border-radius: 24px;
                border: 1px solid var(--ecclesia-border);
                background: var(--ecclesia-bg);
                color: var(--ecclesia-text);
                font-size: 13px;
                min-width: 200px;
                transition: all 0.2s;
                outline: none;
            }
            .ecclesia-search-wrapper input:focus {
                border-color: var(--ecclesia-accent);
                box-shadow: 0 0 0 3px var(--ecclesia-accent)33;
            }
            .search-shortcut {
                position: absolute;
                right: 12px;
                font-size: 10px;
                color: var(--ecclesia-muted);
                background: var(--ecclesia-card);
                padding: 2px 8px;
                border-radius: 4px;
                border: 1px solid var(--ecclesia-border);
                font-weight: 600;
                opacity: 0.6;
            }

            /* ─── Tabs ────────────────────────────────────────────────────────── */
            .ecclesia-tabs {
                display: flex;
                gap: 4px;
                margin-bottom: 20px;
                background: var(--ecclesia-card);
                padding: 4px;
                border-radius: 12px;
                border: 1px solid var(--ecclesia-border);
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }
            .ecclesia-tab {
                padding: 8px 20px;
                border: none;
                border-radius: 8px;
                background: transparent;
                color: var(--ecclesia-muted);
                font-weight: 600;
                font-size: 13px;
                cursor: pointer;
                transition: all 0.2s;
                font-family: inherit;
            }
            .ecclesia-tab:hover {
                background: var(--ecclesia-bg);
                color: var(--ecclesia-text);
            }
            .ecclesia-tab.active {
                background: var(--ecclesia-primary);
                color: #fff;
                box-shadow: 0 2px 8px var(--ecclesia-primary)44;
            }

            /* ─── Panels ──────────────────────────────────────────────────────── */
            .ecclesia-panel {
                display: none;
                animation: fadeIn 0.3s ease;
            }
            .ecclesia-panel.active { display: block; }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* ─── Stats ───────────────────────────────────────────────────────── */
            .ecclesia-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 10px;
                margin-bottom: 20px;
            }
            .stat-card {
                background: var(--ecclesia-card);
                border: 1px solid var(--ecclesia-border);
                border-radius: 12px;
                padding: 14px 18px;
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
            .stat-icon { font-size: 22px; }
            .stat-number {
                font-size: 22px;
                font-weight: 800;
                color: var(--ecclesia-text);
                font-feature-settings: "tnum";
            }
            .stat-label {
                font-size: 10px;
                font-weight: 500;
                color: var(--ecclesia-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            /* ─── Sections ────────────────────────────────────────────────────── */
            .ecclesia-section {
                margin-bottom: 24px;
                background: var(--ecclesia-card);
                border-radius: 16px;
                border: 1px solid var(--ecclesia-border);
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                transition: all 0.2s;
            }
            .ecclesia-section:hover {
                box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            }
            .ecclesia-section-header {
                padding: 14px 20px;
                background: var(--ecclesia-section-bg);
                border-bottom: 1px solid var(--ecclesia-border);
                display: flex;
                align-items: center;
                justify-content: space-between;
                cursor: pointer;
                user-select: none;
                transition: background 0.2s;
            }
            .ecclesia-section-header:hover {
                background: var(--ecclesia-border);
            }
            .ecclesia-section-title {
                display: flex;
                align-items: center;
                gap: 10px;
                font-weight: 700;
                font-size: 14px;
                color: var(--ecclesia-text);
            }
            .ecclesia-section-title .section-icon {
                font-size: 18px;
            }
            .ecclesia-section-count {
                font-size: 11px;
                font-weight: 600;
                color: var(--ecclesia-muted);
                background: var(--ecclesia-bg);
                padding: 1px 10px;
                border-radius: 12px;
            }
            .ecclesia-section-toggle {
                font-size: 12px;
                color: var(--ecclesia-muted);
                transition: transform 0.2s;
            }
            .ecclesia-section-toggle.collapsed {
                transform: rotate(-90deg);
            }
            .ecclesia-section-body {
                padding: 12px 16px 16px;
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
                gap: 8px;
                transition: all 0.3s ease;
            }
            .ecclesia-section-body.collapsed {
                display: none;
            }

            /* ─── Items ───────────────────────────────────────────────────────── */
            .ecclesia-item {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 8px 12px;
                border-radius: 10px;
                background: var(--ecclesia-bg);
                border: 1px solid transparent;
                cursor: pointer;
                transition: all 0.15s;
                position: relative;
            }
            .ecclesia-item:hover {
                border-color: var(--ecclesia-accent);
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            }
            .ecclesia-item .fav-btn {
                position: absolute;
                top: 2px;
                right: 4px;
                background: none;
                border: none;
                cursor: pointer;
                font-size: 12px;
                opacity: 0.2;
                transition: all 0.2s;
                padding: 2px 4px;
            }
            .ecclesia-item .fav-btn:hover {
                opacity: 1;
                transform: scale(1.2);
            }
            .ecclesia-item .fav-btn.active {
                opacity: 1;
                color: #F59E0B;
            }
            .ecclesia-item-icon {
                width: 30px;
                height: 30px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                flex-shrink: 0;
            }
            .ecclesia-item-name {
                font-size: 11px;
                font-weight: 500;
                color: var(--ecclesia-text);
                line-height: 1.3;
                flex: 1;
            }
            .ecclesia-item .open-indicator {
                font-size: 10px;
                color: var(--ecclesia-muted);
                opacity: 0.4;
                transition: opacity 0.2s;
            }
            .ecclesia-item:hover .open-indicator {
                opacity: 1;
            }

            /* ─── Dashboard Items ────────────────────────────────────────────── */
            .ecclesia-dashboard-item {
                background: var(--ecclesia-bg);
                border: 1px solid transparent;
                border-radius: 12px;
                padding: 14px 16px;
                cursor: pointer;
                transition: all 0.2s;
                position: relative;
                text-align: center;
            }
            .ecclesia-dashboard-item:hover {
                border-color: var(--ecclesia-accent);
                transform: translateY(-3px);
                box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            }
            .ecclesia-dashboard-item .fav-btn {
                position: absolute;
                top: 6px;
                right: 8px;
                background: none;
                border: none;
                cursor: pointer;
                font-size: 13px;
                opacity: 0.2;
                transition: all 0.2s;
                padding: 2px 4px;
            }
            .ecclesia-dashboard-item .fav-btn:hover {
                opacity: 1;
                transform: scale(1.2);
            }
            .ecclesia-dashboard-item .fav-btn.active {
                opacity: 1;
                color: #F59E0B;
            }
            .ecclesia-dashboard-icon {
                font-size: 30px;
                margin-bottom: 6px;
                display: block;
            }
            .ecclesia-dashboard-name {
                font-size: 12px;
                font-weight: 700;
                color: var(--ecclesia-text);
                display: block;
            }
            .ecclesia-dashboard-desc {
                font-size: 10px;
                color: var(--ecclesia-muted);
                margin-top: 3px;
                display: block;
            }
            .ecclesia-dashboard-badge {
                display: inline-block;
                font-size: 8px;
                font-weight: 600;
                padding: 1px 8px;
                border-radius: 10px;
                margin-top: 4px;
                background: var(--ecclesia-primary)22;
                color: var(--ecclesia-primary);
            }

            /* ─── Favorites ───────────────────────────────────────────────────── */
            #favorites-container { min-height: 150px; }
            .empty-state {
                text-align: center;
                padding: 40px 20px;
                background: var(--ecclesia-card);
                border-radius: 16px;
                border: 2px dashed var(--ecclesia-border);
            }
            .empty-icon { font-size: 40px; margin-bottom: 10px; }
            .empty-state h3 {
                font-size: 16px;
                color: var(--ecclesia-text);
                margin: 0 0 6px 0;
            }
            .empty-state p {
                color: var(--ecclesia-muted);
                font-size: 13px;
                margin: 0;
            }

            /* ─── Presentation Grid ───────────────────────────────────────────── */
            .presentation-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                gap: 12px;
            }
            .presentation-card {
                background: var(--ecclesia-card);
                border: 1px solid var(--ecclesia-border);
                border-radius: 16px;
                padding: 20px 16px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                position: relative;
                overflow: hidden;
            }
            .presentation-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: var(--ecclesia-gradient);
                opacity: 0;
                transition: opacity 0.3s;
            }
            .presentation-card:hover {
                transform: translateY(-6px) scale(1.02);
                box-shadow: 0 12px 40px rgba(0,0,0,0.1);
                border-color: var(--ecclesia-accent);
            }
            .presentation-card:hover::before {
                opacity: 1;
            }
            .presentation-card .card-icon {
                font-size: 40px;
                display: block;
                margin-bottom: 8px;
            }
            .presentation-card .card-name {
                font-size: 13px;
                font-weight: 700;
                color: var(--ecclesia-text);
                display: block;
            }
            .presentation-card .card-type {
                font-size: 9px;
                font-weight: 600;
                color: var(--ecclesia-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                background: var(--ecclesia-bg);
                padding: 1px 10px;
                border-radius: 10px;
                display: inline-block;
                margin-top: 4px;
            }
            .presentation-card .card-category {
                font-size: 9px;
                color: var(--ecclesia-muted);
                display: block;
                margin-top: 3px;
                opacity: 0.7;
            }

            /* ─── Responsive ──────────────────────────────────────────────────── */
            @media (max-width: 1024px) {
                .ecclesia-section-body {
                    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                }
            }
            @media (max-width: 768px) {
                #ecclesia-root { padding: 12px; }
                .ecclesia-top-bar { flex-direction: column; align-items: stretch; }
                .ecclesia-controls { flex-wrap: wrap; }
                .ecclesia-search-wrapper input { min-width: 100%; }
                .ecclesia-section-body {
                    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
                }
                .ecclesia-stats { grid-template-columns: 1fr 1fr; }
                .ecclesia-tabs { overflow-x: auto; flex-wrap: nowrap; }
                .ecclesia-tab { white-space: nowrap; font-size: 12px; padding: 6px 14px; }
                .presentation-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
            }
            @media (max-width: 480px) {
                .ecclesia-section-body { grid-template-columns: 1fr; }
                .ecclesia-stats { grid-template-columns: 1fr; }
                .presentation-grid { grid-template-columns: 1fr 1fr; }
            }
        </style>
    `;

    // ─── Inject HTML ──────────────────────────────────────────────────────────
    $(page.main).append(html);

    // ─── Initialize ──────────────────────────────────────────────────────────
    const root = document.getElementById('ecclesia-root');
    root.dataset.theme = currentTheme;

    // ─── Helper: Open in new tab ────────────────────────────────────────────
    function openInNewTab(url) {
        const win = window.open(url, '_blank');
        if (win) {
            win.focus();
        } else {
            // Fallback if popup blocked
            window.location.href = url;
        }
    }

    // ─── Render Doctype Sections ──────────────────────────────────────────────
    function renderDoctypeSections(filter = '') {
        const container = document.getElementById('doctype-sections');
        const favorites = JSON.parse(localStorage.getItem('ecclesia-favorites') || '[]');

        // Group doctypes by category
        const grouped = {};
        DOCTYPES.forEach(d => {
            if (!grouped[d.category]) grouped[d.category] = [];
            grouped[d.category].push(d);
        });

        // Sort categories by order
        const sortedCategories = Object.keys(DOCTYPE_CATEGORIES)
            .filter(cat => grouped[cat] && grouped[cat].length > 0)
            .sort((a, b) => (DOCTYPE_CATEGORIES[a].order || 99) - (DOCTYPE_CATEGORIES[b].order || 99));

        let html = '';
        sortedCategories.forEach(cat => {
            const items = grouped[cat];
            const filtered = items.filter(d => 
                d.name.toLowerCase().includes(filter.toLowerCase()) ||
                d.category.toLowerCase().includes(filter.toLowerCase())
            );

            if (filtered.length === 0) return;

            const catInfo = DOCTYPE_CATEGORIES[cat] || { icon: '📁', color: '#6B7280' };

            html += `
                <div class="ecclesia-section">
                    <div class="ecclesia-section-header" onclick="toggleSection(this)">
                        <div class="ecclesia-section-title">
                            <span class="section-icon">${catInfo.icon}</span>
                            ${cat}
                            <span class="ecclesia-section-count">${filtered.length}</span>
                        </div>
                        <span class="ecclesia-section-toggle">▼</span>
                    </div>
                    <div class="ecclesia-section-body">
                        ${filtered.map(d => {
                            const isFav = favorites.includes(d.name);
                            const color = d.color || catInfo.color || '#8B5CF6';
                            return `
                                <div class="ecclesia-item" onclick="openEcclesia('List', '${d.name}')">
                                    <button class="fav-btn ${isFav ? 'active' : ''}" 
                                            onclick="event.stopPropagation(); toggleFavorite('${d.name}', 'doctype')">
                                        ${isFav ? '⭐' : '☆'}
                                    </button>
                                    <div class="ecclesia-item-icon" style="background:${color}22;color:${color}">
                                        ${d.icon}
                                    </div>
                                    <span class="ecclesia-item-name">${d.name}</span>
                                    <span class="open-indicator">↗</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html || '<div class="empty-state"><div class="empty-icon">🔍</div><h3>No results found</h3><p>Try adjusting your search</p></div>';
    }

    // ─── Render Dashboard Sections ──────────────────────────────────────────
    function renderDashboardSections(filter = '') {
        const container = document.getElementById('dashboard-sections');
        const favorites = JSON.parse(localStorage.getItem('ecclesia-favorites') || '[]');

        // Group dashboards by category
        const grouped = {};
        DASHBOARDS.forEach(d => {
            if (!grouped[d.category]) grouped[d.category] = [];
            grouped[d.category].push(d);
        });

        // Sort categories by order
        const sortedCategories = Object.keys(DASHBOARD_CATEGORIES)
            .filter(cat => grouped[cat] && grouped[cat].length > 0)
            .sort((a, b) => (DASHBOARD_CATEGORIES[a].order || 99) - (DASHBOARD_CATEGORIES[b].order || 99));

        let html = '';
        sortedCategories.forEach(cat => {
            const items = grouped[cat];
            const filtered = items.filter(d => 
                d.name.toLowerCase().includes(filter.toLowerCase()) ||
                d.desc.toLowerCase().includes(filter.toLowerCase()) ||
                d.category.toLowerCase().includes(filter.toLowerCase())
            );

            if (filtered.length === 0) return;

            const catInfo = DASHBOARD_CATEGORIES[cat] || { icon: '📊', color: '#6B7280' };

            html += `
                <div class="ecclesia-section">
                    <div class="ecclesia-section-header" onclick="toggleSection(this)">
                        <div class="ecclesia-section-title">
                            <span class="section-icon">${catInfo.icon}</span>
                            ${cat}
                            <span class="ecclesia-section-count">${filtered.length}</span>
                        </div>
                        <span class="ecclesia-section-toggle">▼</span>
                    </div>
                    <div class="ecclesia-section-body" style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));">
                        ${filtered.map(d => {
                            const isFav = favorites.includes(d.id);
                            const color = d.color || '#8B5CF6';
                            return `
                                <div class="ecclesia-dashboard-item" onclick="openEcclesia('${d.id}')">
                                    <button class="fav-btn ${isFav ? 'active' : ''}" 
                                            onclick="event.stopPropagation(); toggleFavorite('${d.id}', 'dashboard')">
                                        ${isFav ? '⭐' : '☆'}
                                    </button>
                                    <span class="ecclesia-dashboard-icon">${d.icon}</span>
                                    <span class="ecclesia-dashboard-name">${d.name}</span>
                                    <span class="ecclesia-dashboard-desc">${d.desc}</span>
                                    <span class="ecclesia-dashboard-badge" style="background:${color}22;color:${color}">Launch ↗</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html || '<div class="empty-state"><div class="empty-icon">🔍</div><h3>No results found</h3><p>Try adjusting your search</p></div>';
    }

    // ─── Render Favorites ───────────────────────────────────────────────────
    function renderFavorites() {
        const container = document.getElementById('favorites-container');
        const favorites = JSON.parse(localStorage.getItem('ecclesia-favorites') || '[]');

        if (favorites.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⭐</div>
                    <h3>No favorites yet</h3>
                    <p>Click the star icon on any doctype or dashboard to save it here</p>
                </div>
            `;
            return;
        }

        const favDoctypes = DOCTYPES.filter(d => favorites.includes(d.name));
        const favDashboards = DASHBOARDS.filter(d => favorites.includes(d.id));

        let html = '';
        
        if (favDoctypes.length > 0) {
            html += `
                <div class="ecclesia-section">
                    <div class="ecclesia-section-header" onclick="toggleSection(this)">
                        <div class="ecclesia-section-title">
                            <span class="section-icon">📋</span>
                            Favorite Doctypes
                            <span class="ecclesia-section-count">${favDoctypes.length}</span>
                        </div>
                        <span class="ecclesia-section-toggle">▼</span>
                    </div>
                    <div class="ecclesia-section-body">
                        ${favDoctypes.map(d => `
                            <div class="ecclesia-item" onclick="openEcclesia('List', '${d.name}')">
                                <button class="fav-btn active" onclick="event.stopPropagation(); toggleFavorite('${d.name}', 'doctype')">⭐</button>
                                <div class="ecclesia-item-icon" style="background:${d.color}22;color:${d.color}">${d.icon}</div>
                                <span class="ecclesia-item-name">${d.name}</span>
                                <span class="open-indicator">↗</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        if (favDashboards.length > 0) {
            html += `
                <div class="ecclesia-section">
                    <div class="ecclesia-section-header" onclick="toggleSection(this)">
                        <div class="ecclesia-section-title">
                            <span class="section-icon">📊</span>
                            Favorite Dashboards
                            <span class="ecclesia-section-count">${favDashboards.length}</span>
                        </div>
                        <span class="ecclesia-section-toggle">▼</span>
                    </div>
                    <div class="ecclesia-section-body" style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));">
                        ${favDashboards.map(d => `
                            <div class="ecclesia-dashboard-item" onclick="openEcclesia('${d.id}')">
                                <button class="fav-btn active" onclick="event.stopPropagation(); toggleFavorite('${d.id}', 'dashboard')">⭐</button>
                                <span class="ecclesia-dashboard-icon">${d.icon}</span>
                                <span class="ecclesia-dashboard-name">${d.name}</span>
                                <span class="ecclesia-dashboard-desc">${d.desc}</span>
                                <span class="ecclesia-dashboard-badge" style="background:${d.color}22;color:${d.color}">Launch ↗</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    // ─── Render Presentation ──────────────────────────────────────────────────
    function renderPresentation() {
        const container = document.getElementById('presentation-grid');
        const allItems = [
            ...DOCTYPES.map(d => ({ ...d, type: 'doctype', route: `List/${d.name}` })),
            ...DASHBOARDS.map(d => ({ ...d, type: 'dashboard', route: d.id }))
        ];

        container.innerHTML = allItems.map(item => `
            <div class="presentation-card" onclick="openEcclesia('${item.route}')">
                <span class="card-icon">${item.icon}</span>
                <span class="card-name">${item.name}</span>
                <span class="card-type">${item.type}</span>
                <span class="card-category">${item.category || ''}</span>
            </div>
        `).join('');
    }

    // ─── Toggle Section ──────────────────────────────────────────────────────
    window.toggleSection = function(header) {
        const body = header.nextElementSibling;
        const toggle = header.querySelector('.ecclesia-section-toggle');
        if (body.classList.contains('collapsed')) {
            body.classList.remove('collapsed');
            toggle.classList.remove('collapsed');
            toggle.textContent = '▼';
        } else {
            body.classList.add('collapsed');
            toggle.classList.add('collapsed');
            toggle.textContent = '▶';
        }
    };

    // ─── Toggle Favorite ────────────────────────────────────────────────────
    window.toggleFavorite = function(id, type) {
        let favorites = JSON.parse(localStorage.getItem('ecclesia-favorites') || '[]');
        const index = favorites.indexOf(id);
        if (index > -1) {
            favorites.splice(index, 1);
        } else {
            favorites.push(id);
        }
        localStorage.setItem('ecclesia-favorites', JSON.stringify(favorites));
        
        // Refresh all views
        const searchVal = document.getElementById('ecclesia-search').value;
        const activeTab = document.querySelector('.ecclesia-tab.active').dataset.tab;
        
        if (activeTab === 'doctypes') renderDoctypeSections(searchVal);
        else if (activeTab === 'dashboards') renderDashboardSections(searchVal);
        else if (activeTab === 'favorites') renderFavorites();
        else if (activeTab === 'presentation') renderPresentation();
        
        updateStats();
    };

    // ─── Open Ecclesia Item ──────────────────────────────────────────────────
    window.openEcclesia = function(type, name) {
        let url;
        if (type === 'List') {
            url = `/app/list/${name}`;
        } else {
            url = `/app/${type}`;
        }
        openInNewTab(url);
    };

    // ─── Update Stats ───────────────────────────────────────────────────────
    function updateStats() {
        const favorites = JSON.parse(localStorage.getItem('ecclesia-favorites') || '[]');
        document.getElementById('favorite-count').textContent = favorites.length;
        document.getElementById('fav-doctype-count').textContent = 
            favorites.filter(f => DOCTYPES.some(d => d.name === f)).length;
        document.getElementById('fav-dashboard-count').textContent = 
            favorites.filter(f => DASHBOARDS.some(d => d.id === f)).length;
    }

    // ─── Tab Switching ──────────────────────────────────────────────────────
    document.querySelectorAll('.ecclesia-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.ecclesia-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            const panelId = this.dataset.tab;
            document.querySelectorAll('.ecclesia-panel').forEach(p => p.classList.remove('active'));
            document.querySelector(`.ecclesia-panel[data-panel="${panelId}"]`).classList.add('active');
            
            const searchVal = document.getElementById('ecclesia-search').value;
            if (panelId === 'doctypes') renderDoctypeSections(searchVal);
            else if (panelId === 'dashboards') renderDashboardSections(searchVal);
            else if (panelId === 'favorites') renderFavorites();
            else if (panelId === 'presentation') renderPresentation();
        });
    });

    // ─── Theme Switching ────────────────────────────────────────────────────
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const theme = this.dataset.theme;
            root.dataset.theme = theme;
            localStorage.setItem('ecclesia-theme', theme);
            document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentTheme = theme;
        });
    });

    // ─── Search ─────────────────────────────────────────────────────────────
    document.getElementById('ecclesia-search').addEventListener('input', function() {
        const val = this.value;
        const activeTab = document.querySelector('.ecclesia-tab.active').dataset.tab;
        if (activeTab === 'doctypes') renderDoctypeSections(val);
        else if (activeTab === 'dashboards') renderDashboardSections(val);
    });

    // ─── Keyboard Shortcuts ──────────────────────────────────────────────────
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('ecclesia-search').focus();
        }
        if (e.key === 'Escape') {
            document.getElementById('ecclesia-search').blur();
        }
    });

    // ─── Initial Render ─────────────────────────────────────────────────────
    renderDoctypeSections('');
    renderDashboardSections('');
    renderFavorites();
    renderPresentation();
    updateStats();

    // ─── Expose for debugging ──────────────────────────────────────────────
    window.Ecclesia = { DOCTYPES, DASHBOARDS, THEMES, openEcclesia, toggleFavorite, toggleSection };
};