// ecclesia/ecclesia/page/admin-shc/admin-shc.js
// Admin Shortcut — Vertical Tab Layout with 3-Column Groups
// Tabs: Doctypes | Reports | Dashboards | Favorites

frappe.pages['admin-shc'] = frappe.pages['admin-shc'] || {};

frappe.pages['admin-shc'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '🏛️ Admin Shortcut',
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

    const savedTheme = localStorage.getItem('admin_shc_theme') || 'corporate';
    let currentTheme = savedTheme;

    // ─── Vertical Tabs ────────────────────────────────────────────────────────
    const TABS = [
        { id: 'doctypes', label: '📋 Doctypes', icon: '📋' },
        { id: 'reports', label: '📊 Reports', icon: '📊' },
        { id: 'dashboards', label: '📈 Dashboards', icon: '📈' },
        { id: 'favorites', label: '⭐ Favorites', icon: '⭐' }
    ];

    // ─── DOCTYPE GROUPS (3 Columns) ──────────────────────────────────────────
    const DOCTYPE_GROUPS = [
        // ─── Column 1 ──────────────────────────────────────────────────────────
        {
            id: 'masters',
            name: '📋 Masters',
            icon: '📋',
            color: '#475569',
            items: [
                { name: 'Facility', icon: '🏗️', color: '#3B82F6' },
                { name: 'Utility Meter', icon: '📊', color: '#059669' },
                { name: 'Company Vehicle', icon: '🚗', color: '#F59E0B' },
                { name: 'Service Provider', icon: '🔧', color: '#8B5CF6' },
                { name: 'Compliance Register', icon: '📜', color: '#7C3AED' },
                { name: 'Supplier', icon: '🏢', color: '#06B6D4' },
                { name: 'Supplier Group', icon: '📂', color: '#475569' },
                { name: 'Contact', icon: '📇', color: '#3B82F6' },
                { name: 'Address', icon: '📍', color: '#10B981' }
            ]
        },
        {
            id: 'items-pricing',
            name: '🏷️ Items & Pricing',
            icon: '🏷️',
            color: '#F59E0B',
            items: [
                { name: 'Item', icon: '📦', color: '#F59E0B' },
                { name: 'Item Group', icon: '📂', color: '#8B5CF6' },
                { name: 'Item Price', icon: '💰', color: '#059669' },
                { name: 'Price List', icon: '📋', color: '#3B82F6' },
                { name: 'Product Bundle', icon: '📦', color: '#7C3AED' },
                { name: 'Promotional Scheme', icon: '🎯', color: '#F97316' },
                { name: 'Pricing Rule', icon: '⚖️', color: '#EF4444' },
                { name: 'Item Alternative', icon: '🔄', color: '#06B6D4' },
                { name: 'Manufacturer', icon: '🏭', color: '#1E293B' }
            ]
        },
        {
            id: 'settings',
            name: '⚙️ Settings',
            icon: '⚙️',
            color: '#6B7280',
            items: [
                { name: 'Buying Settings', icon: '⚙️', color: '#6B7280' },
                { name: 'Purchase Taxes and Charges Template', icon: '🧾', color: '#F59E0B' },
                { name: 'Terms and Conditions Template', icon: '📄', color: '#8B5CF6' },
                { name: 'Stock Settings', icon: '📦', color: '#059669' },
                { name: 'Warehouse', icon: '🏚️', color: '#F97316' },
                { name: 'Unit of Measure (UOM)', icon: '📐', color: '#3B82F6' },
                { name: 'Item Variant Settings', icon: '🔀', color: '#7C3AED' },
                { name: 'Brand', icon: '🏷️', color: '#EF4444' },
                { name: 'Item Attribute', icon: '🔖', color: '#06B6D4' },
                { name: 'UOM Conversion Factor', icon: '🔄', color: '#10B981' },
                { name: 'Shipping Rule', icon: '🚚', color: '#F59E0B' }
            ]
        },
        // ─── Column 2 ──────────────────────────────────────────────────────────
        {
            id: 'compliance',
            name: '⚖️ Compliance Management',
            icon: '⚖️',
            color: '#7C3AED',
            items: [
                { name: 'Compliance Register', icon: '📜', color: '#7C3AED' },
                { name: 'Compliance Calendar', icon: '📅', color: '#8B5CF6' },
                { name: 'Compliance Audit', icon: '🔍', color: '#F59E0B' },
                { name: 'Compliance Task', icon: '✅', color: '#10B981' },
                { name: 'Compliance Incident', icon: '⚠️', color: '#EF4444' },
                { name: 'Compliance Exception', icon: '🚫', color: '#F97316' },
                { name: 'Compliance Filing', icon: '📁', color: '#3B82F6' },
                { name: 'Compliance Event Log', icon: '📝', color: '#6B7280' },
                { name: 'Compliance Policy', icon: '📋', color: '#1E293B' },
                { name: 'Compliance Rule', icon: '⚖️', color: '#475569' },
                { name: 'Compliance Period', icon: '📅', color: '#8B5CF6' },
                { name: 'Compliance Risk Register', icon: '⚠️', color: '#EF4444' }
            ]
        },
        {
            id: 'statutory',
            name: '📋 Statutory & HR Compliance',
            icon: '📋',
            color: '#1E293B',
            items: [
                { name: 'Labour Compliance Tracker', icon: '👷', color: '#F59E0B' },
                { name: 'ITF Assessment', icon: '📊', color: '#3B82F6' },
                { name: 'NSITF Assessment', icon: '🛡️', color: '#EF4444' },
                { name: 'NHF Remittance Batch', icon: '🏦', color: '#10B981' },
                { name: 'Pension Remittance Batch', icon: '💰', color: '#8B5CF6' },
                { name: 'Conflict of Interest Declaration', icon: '📄', color: '#F97316' },
                { name: 'Expatriate Permit Register', icon: '🌍', color: '#06B6D4' },
                { name: 'Regulatory Authority', icon: '🏛️', color: '#475569' },
                { name: 'Regulatory Return', icon: '📊', color: '#059669' },
                { name: 'Statutory Register Entry', icon: '📚', color: '#6B7280' }
            ]
        },
        {
            id: 'legal',
            name: '📜 Legal & Regulatory',
            icon: '📜',
            color: '#8B5CF6',
            items: [
                { name: 'License and Permit', icon: '🎫', color: '#8B5CF6' },
                { name: 'License Management', icon: '📋', color: '#7C3AED' },
                { name: 'Board Resolution', icon: '📄', color: '#1E293B' },
                { name: 'Contract Compliance Record', icon: '📑', color: '#F59E0B' },
                { name: 'Corporate Compliance Register', icon: '🏢', color: '#475569' },
                { name: 'Data Breach Register', icon: '🔓', color: '#EF4444' },
                { name: 'Data Processing Record', icon: '📊', color: '#3B82F6' },
                { name: 'Environmental Compliance Record', icon: '🌿', color: '#10B981' }
            ]
        },
        // ─── Column 3 ──────────────────────────────────────────────────────────
        {
            id: 'purchasing',
            name: '🛒 Purchasing',
            icon: '🛒',
            color: '#3B82F6',
            items: [
                { name: 'Material Request', icon: '📋', color: '#3B82F6' },
                { name: 'Purchase Order', icon: '📄', color: '#F59E0B' },
                { name: 'Purchase Invoice', icon: '🧾', color: '#EF4444' },
                { name: 'Request for Quotation', icon: '📨', color: '#8B5CF6' },
                { name: 'Supplier Quotation', icon: '💬', color: '#10B981' },
                { name: 'Purchase Receipt', icon: '📦', color: '#059669' },
                { name: 'Supplier Scorecard', icon: '📊', color: '#7C3AED' },
                { name: 'Supplier Scorecard Variable', icon: '📈', color: '#F97316' },
                { name: 'Supplier Scorecard Criteria', icon: '🎯', color: '#06B6D4' },
                { name: 'Supplier Scorecard Standing', icon: '🏆', color: '#1E293B' }
            ]
        },
        {
            id: 'stock-transactions',
            name: '📦 Stock Transactions',
            icon: '📦',
            color: '#059669',
            items: [
                { name: 'Stock Entry', icon: '📥', color: '#059669' },
                { name: 'Delivery Note', icon: '📤', color: '#F59E0B' },
                { name: 'Delivery Trip', icon: '🚚', color: '#3B82F6' },
                { name: 'Pick List', icon: '📋', color: '#8B5CF6' },
                { name: 'Stock Reconciliation', icon: '🔄', color: '#F97316' },
                { name: 'Landed Cost Voucher', icon: '💰', color: '#EF4444' },
                { name: 'Packing Slip', icon: '📦', color: '#10B981' },
                { name: 'Quality Inspection', icon: '✅', color: '#7C3AED' },
                { name: 'Quality Inspection Template', icon: '📋', color: '#475569' }
            ]
        },
        {
            id: 'facilities',
            name: '🏗️ Facilities & Assets',
            icon: '🏗️',
            color: '#3B82F6',
            items: [
                { name: 'Facility', icon: '🏗️', color: '#3B82F6' },
                { name: 'Facility Maintenance Request', icon: '🔧', color: '#F59E0B' },
                { name: 'Maintenance Work Order', icon: '📋', color: '#F97316' },
                { name: 'Asset Inspection', icon: '🔍', color: '#10B981' },
                { name: 'Asset Disposal Request', icon: '🗑️', color: '#EF4444' },
                { name: 'Utility Meter', icon: '📊', color: '#059669' },
                { name: 'Utility Consumption', icon: '⚡', color: '#8B5CF6' },
                { name: 'Generator Log', icon: '⚡', color: '#F59E0B' }
            ]
        },
        {
            id: 'transport',
            name: '🚗 Transport & Logistics',
            icon: '🚗',
            color: '#F59E0B',
            items: [
                { name: 'Company Vehicle', icon: '🚗', color: '#F59E0B' },
                { name: 'Vehicle Request', icon: '📝', color: '#3B82F6' },
                { name: 'Vehicle Trip Log', icon: '📋', color: '#10B981' },
                { name: 'Fuel Issue', icon: '⛽', color: '#F97316' }
            ]
        },
        {
            id: 'bookings',
            name: '🏨 Bookings & Meetings',
            icon: '🏨',
            color: '#06B6D4',
            items: [
                { name: 'Meeting Room Booking', icon: '🏢', color: '#3B82F6' },
                { name: 'Guest House Booking', icon: '🏨', color: '#10B981' },
                { name: 'Service Contract', icon: '📄', color: '#8B5CF6' },
                { name: 'Service Provider', icon: '🔧', color: '#F59E0B' }
            ]
        },
        {
            id: 'requests',
            name: '📨 Administrative Requests',
            icon: '📨',
            color: '#3B82F6',
            items: [
                { name: 'Administrative Request', icon: '📨', color: '#3B82F6' },
                { name: 'Visitor Register', icon: '👤', color: '#8B5CF6' },
                { name: 'Security Incident', icon: '🛡️', color: '#EF4444' },
                { name: 'HSE Inspection', icon: '🔍', color: '#10B981' },
                { name: 'Emergency Drill', icon: '🚨', color: '#F97316' }
            ]
        },
        {
            id: 'finance-admin',
            name: '💰 Admin Finance',
            icon: '💰',
            color: '#059669',
            items: [
                { name: 'Admin Budget', icon: '📊', color: '#059669' },
                { name: 'Admin Expense', icon: '💳', color: '#EF4444' },
                { name: 'Compliance Liability Ledger', icon: '📒', color: '#F59E0B' },
                { name: 'Compliance Payment Allocation', icon: '💵', color: '#10B981' },
                { name: 'Compliance KPI Snapshot', icon: '📈', color: '#7C3AED' }
            ]
        }
    ];

    // ─── REPORT GROUPS (3 Columns) ───────────────────────────────────────────
    const REPORT_GROUPS = [
        {
            id: 'compliance-reports',
            name: '⚖️ Compliance Reports',
            icon: '⚖️',
            color: '#7C3AED',
            items: [
                { name: 'Compliance Summary Report', icon: '📊', color: '#7C3AED' },
                { name: 'Compliance Audit Report', icon: '🔍', color: '#F59E0B' },
                { name: 'Compliance Incident Report', icon: '⚠️', color: '#EF4444' },
                { name: 'Compliance Calendar Report', icon: '📅', color: '#3B82F6' },
                { name: 'Compliance Filing Status Report', icon: '📁', color: '#10B981' },
                { name: 'Compliance KPI Report', icon: '📈', color: '#8B5CF6' },
                { name: 'Compliance Risk Register Report', icon: '📋', color: '#F97316' }
            ]
        },
        {
            id: 'purchase-analytics',
            name: '📊 Purchase Analytics',
            icon: '📊',
            color: '#3B82F6',
            items: [
                { name: 'Purchase Analytics', icon: '📊', color: '#3B82F6' },
                { name: 'Purchase Order Analysis', icon: '📈', color: '#F59E0B' },
                { name: 'Supplier-Wise Sales Analytics', icon: '🏢', color: '#8B5CF6' },
                { name: 'Items to Order and Receive', icon: '📋', color: '#059669' },
                { name: 'Purchase Order Trends', icon: '📈', color: '#F97316' },
                { name: 'Procurement Tracker', icon: '🔍', color: '#7C3AED' },
                { name: 'Purchase Receipt Trends', icon: '📊', color: '#10B981' },
                { name: 'Purchase Invoice Trends', icon: '📊', color: '#EF4444' },
                { name: 'Supplier Quotation Comparison', icon: '📄', color: '#06B6D4' }
            ]
        },
        {
            id: 'purchase-reports',
            name: '📋 Purchase Reports',
            icon: '📋',
            color: '#F59E0B',
            items: [
                { name: 'Items To Be Requested', icon: '📋', color: '#3B82F6' },
                { name: 'Item-wise Purchase History', icon: '📚', color: '#8B5CF6' },
                { name: 'Subcontracted Raw Materials To Be Transferred', icon: '🔄', color: '#F97316' },
                { name: 'Subcontracted Item To Be Received', icon: '📦', color: '#10B981' },
                { name: 'Material Requests without Supplier Quotations', icon: '📨', color: '#EF4444' },
                { name: 'Supplier Addresses And Contacts', icon: '📍', color: '#059669' }
            ]
        },
        {
            id: 'stock-reports',
            name: '📦 Stock Reports',
            icon: '📦',
            color: '#059669',
            items: [
                { name: 'Stock Analytics', icon: '📊', color: '#059669' },
                { name: 'Stock Ledger', icon: '📒', color: '#3B82F6' },
                { name: 'Stock Balance', icon: '⚖️', color: '#F59E0B' },
                { name: 'Stock Projected Qty', icon: '📈', color: '#8B5CF6' },
                { name: 'Stock Summary', icon: '📋', color: '#7C3AED' },
                { name: 'Stock Ageing', icon: '⏳', color: '#F97316' },
                { name: 'Item Price', icon: '💰', color: '#10B981' },
                { name: 'Stock Warehouse Wise Stock Balance', icon: '🏚️', color: '#EF4444' },
                { name: 'Batch-Wise Balance History', icon: '📚', color: '#06B6D4' }
            ]
        },
        {
            id: 'stock-transactions-report',
            name: '📥 Stock Transactions Reports',
            icon: '📥',
            color: '#3B82F6',
            items: [
                { name: 'Delivery Note Trends', icon: '📤', color: '#F59E0B' },
                { name: 'Purchase Receipt Trends', icon: '📦', color: '#059669' },
                { name: 'Sales Order Analysis', icon: '📈', color: '#8B5CF6' },
                { name: 'Purchase Order Analysis', icon: '📊', color: '#F97316' },
                { name: 'Item Shortage Report', icon: '⚠️', color: '#EF4444' },
                { name: 'Requested Items To Be Transferred', icon: '🔄', color: '#10B981' }
            ]
        },
        {
            id: 'stock-other',
            name: '🔍 Other Stock Reports',
            icon: '🔍',
            color: '#7C3AED',
            items: [
                { name: 'Batch Item Expiry Status', icon: '⏰', color: '#EF4444' },
                { name: 'Item Prices', icon: '💰', color: '#059669' },
                { name: 'Itemwise Recommended Reorder Level', icon: '📊', color: '#F59E0B' },
                { name: 'Item Variant Details', icon: '🔀', color: '#8B5CF6' },
                { name: 'Subcontracted Raw Materials To Be Transferred', icon: '🔄', color: '#F97316' },
                { name: 'Subcontracted Item To Be Received', icon: '📦', color: '#10B981' }
            ]
        },
        {
            id: 'facility-reports',
            name: '🏗️ Facilities & Maintenance',
            icon: '🏗️',
            color: '#3B82F6',
            items: [
                { name: 'Facility Maintenance Report', icon: '🔧', color: '#F59E0B' },
                { name: 'Maintenance Work Order Report', icon: '📋', color: '#F97316' },
                { name: 'Asset Inspection Report', icon: '🔍', color: '#10B981' },
                { name: 'Utility Consumption Report', icon: '⚡', color: '#059669' },
                { name: 'Facility Utilization Report', icon: '📊', color: '#3B82F6' }
            ]
        },
        {
            id: 'transport-reports',
            name: '🚗 Transport Reports',
            icon: '🚗',
            color: '#F59E0B',
            items: [
                { name: 'Vehicle Utilization Report', icon: '📊', color: '#F59E0B' },
                { name: 'Trip Log Analysis Report', icon: '📋', color: '#10B981' },
                { name: 'Fuel Consumption Report', icon: '⛽', color: '#F97316' },
                { name: 'Vehicle Maintenance Report', icon: '🔧', color: '#3B82F6' },
                { name: 'Fleet Performance Report', icon: '📈', color: '#8B5CF6' }
            ]
        },
        {
            id: 'admin-reports',
            name: '📨 Administrative Reports',
            icon: '📨',
            color: '#3B82F6',
            items: [
                { name: 'Administrative Request Report', icon: '📨', color: '#3B82F6' },
                { name: 'Visitor Register Report', icon: '👤', color: '#8B5CF6' },
                { name: 'Security Incident Report', icon: '🛡️', color: '#EF4444' },
                { name: 'HSE Inspection Report', icon: '🔍', color: '#10B981' },
                { name: 'Emergency Drill Report', icon: '🚨', color: '#F97316' },
                { name: 'Meeting Room Utilization Report', icon: '🏢', color: '#06B6D4' },
                { name: 'Guest House Booking Report', icon: '🏨', color: '#059669' }
            ]
        },
        {
            id: 'financial-reports',
            name: '💰 Financial Reports',
            icon: '💰',
            color: '#059669',
            items: [
                { name: 'Admin Budget Report', icon: '📊', color: '#059669' },
                { name: 'Admin Expense Report', icon: '💳', color: '#EF4444' },
                { name: 'Budget vs Actual Report', icon: '📈', color: '#3B82F6' },
                { name: 'Statutory Payment Report', icon: '🏦', color: '#8B5CF6' },
                { name: 'Compliance Cost Report', icon: '💰', color: '#F59E0B' }
            ]
        },
        {
            id: 'statutory-reports',
            name: '📋 Statutory Reports',
            icon: '📋',
            color: '#1E293B',
            items: [
                { name: 'Labour Compliance Report', icon: '👷', color: '#F59E0B' },
                { name: 'ITF Compliance Report', icon: '📊', color: '#3B82F6' },
                { name: 'NSITF Compliance Report', icon: '🛡️', color: '#EF4444' },
                { name: 'Pension Remittance Report', icon: '💰', color: '#8B5CF6' },
                { name: 'NHF Remittance Report', icon: '🏦', color: '#10B981' },
                { name: 'Expatriate Permit Report', icon: '🌍', color: '#06B6D4' }
            ]
        },
        {
            id: 'executive-admin',
            name: '👔 Executive Admin Reports',
            icon: '👔',
            color: '#1E293B',
            items: [
                { name: 'Admin Operations Dashboard', icon: '📊', color: '#1E293B' },
                { name: 'Compliance Executive Summary', icon: '📈', color: '#7C3AED' },
                { name: 'Facility Performance Report', icon: '🏗️', color: '#3B82F6' },
                { name: 'Fleet Performance Dashboard', icon: '🚗', color: '#F59E0B' },
                { name: 'Admin Financial Summary', icon: '💰', color: '#059669' },
                { name: 'Statutory Compliance Report', icon: '📋', color: '#8B5CF6' },
                { name: 'Purchase Executive Dashboard', icon: '🛒', color: '#F97316' },
                { name: 'Stock Executive Dashboard', icon: '📦', color: '#10B981' }
            ]
        }
    ];

    // ─── DASHBOARDS (3 Columns) ──────────────────────────────────────────────
    const DASHBOARD_GROUPS = [
        {
            id: 'admin-command',
            name: '🏛️ Admin Command Centers',
            icon: '🏛️',
            color: '#1E293B',
            items: [
                { name: 'admin-dashboard', icon: '📊', color: '#1E293B', desc: 'Admin operations overview' },
                { name: 'facility-dsh', icon: '🏗️', color: '#3B82F6', desc: 'Facility management' },
                { name: 'fleet-dsh', icon: '🚗', color: '#F59E0B', desc: 'Fleet operations' },
                { name: 'compliance-dsh', icon: '⚖️', color: '#7C3AED', desc: 'Compliance management' }
            ]
        },
        {
            id: 'compliance-analytics',
            name: '⚖️ Compliance Analytics',
            icon: '⚖️',
            color: '#7C3AED',
            items: [
                { name: 'compliance-calendar-dsh', icon: '📅', color: '#8B5CF6', desc: 'Compliance calendar' },
                { name: 'risk-register-dsh', icon: '⚠️', color: '#EF4444', desc: 'Risk register' },
                { name: 'compliance-kpi-dsh', icon: '📈', color: '#10B981', desc: 'KPI tracking' },
                { name: 'audit-trail-dsh', icon: '🔍', color: '#F59E0B', desc: 'Audit trail' }
            ]
        },
        {
            id: 'procurement',
            name: '🛒 Procurement Dashboards',
            icon: '🛒',
            color: '#3B82F6',
            items: [
                { name: 'procurement-dsh', icon: '📊', color: '#3B82F6', desc: 'Procurement operations' },
                { name: 'purchase-order-dsh', icon: '📋', color: '#F59E0B', desc: 'Purchase order tracking' },
                { name: 'supplier-dsh', icon: '🏢', color: '#8B5CF6', desc: 'Supplier management' },
                { name: 'purchase-analytics-dsh', icon: '📈', color: '#059669', desc: 'Purchase analytics' }
            ]
        },
        {
            id: 'stock',
            name: '📦 Stock Dashboards',
            icon: '📦',
            color: '#059669',
            items: [
                { name: 'stock-dsh', icon: '📊', color: '#059669', desc: 'Stock management' },
                { name: 'inventory-dsh', icon: '📦', color: '#3B82F6', desc: 'Inventory tracking' },
                { name: 'warehouse-dsh', icon: '🏚️', color: '#F59E0B', desc: 'Warehouse operations' },
                { name: 'stock-balance-dsh', icon: '⚖️', color: '#8B5CF6', desc: 'Stock balance' }
            ]
        },
        {
            id: 'facilities',
            name: '🏗️ Facilities & Maintenance',
            icon: '🏗️',
            color: '#3B82F6',
            items: [
                { name: 'maintenance-dsh', icon: '🔧', color: '#F59E0B', desc: 'Maintenance tracking' },
                { name: 'utility-dsh', icon: '⚡', color: '#059669', desc: 'Utility consumption' },
                { name: 'asset-dsh', icon: '🔍', color: '#10B981', desc: 'Asset inspection' }
            ]
        },
        {
            id: 'transport',
            name: '🚗 Transport & Logistics',
            icon: '🚗',
            color: '#F59E0B',
            items: [
                { name: 'vehicle-dsh', icon: '🚗', color: '#F59E0B', desc: 'Vehicle management' },
                { name: 'trip-log-dsh', icon: '📋', color: '#10B981', desc: 'Trip log analysis' },
                { name: 'fuel-dsh', icon: '⛽', color: '#F97316', desc: 'Fuel management' }
            ]
        },
        {
            id: 'statutory',
            name: '📋 Statutory & HR Compliance',
            icon: '📋',
            color: '#1E293B',
            items: [
                { name: 'statutory-dsh', icon: '📊', color: '#8B5CF6', desc: 'Statutory compliance' },
                { name: 'hr-compliance-dsh', icon: '👷', color: '#F59E0B', desc: 'HR compliance' },
                { name: 'remittance-dsh', icon: '🏦', color: '#10B981', desc: 'Remittance tracking' }
            ]
        },
        {
            id: 'data-privacy',
            name: '🔐 Data & Privacy',
            icon: '🔐',
            color: '#06B6D4',
            items: [
                { name: 'privacy-dsh', icon: '🔐', color: '#06B6D4', desc: 'Data privacy' },
                { name: 'breach-dsh', icon: '🔓', color: '#EF4444', desc: 'Breach management' }
            ]
        }
    ];

    // ─── DAILY OPERATIONS ────────────────────────────────────────────────────
    const DAILY_OPS = [
        { name: 'Administrative Request', icon: '📨', color: '#3B82F6' },
        { name: 'Facility Maintenance Request', icon: '🔧', color: '#F59E0B' },
        { name: 'Vehicle Request', icon: '🚗', color: '#F59E0B' },
        { name: 'Meeting Room Booking', icon: '🏢', color: '#3B82F6' },
        { name: 'Guest House Booking', icon: '🏨', color: '#10B981' },
        { name: 'Fuel Issue', icon: '⛽', color: '#F97316' },
        { name: 'Material Request', icon: '📋', color: '#3B82F6' },
        { name: 'Purchase Order', icon: '📄', color: '#F59E0B' },
        { name: 'Stock Entry', icon: '📥', color: '#059669' },
        { name: 'Visitor Register', icon: '👤', color: '#8B5CF6' },
        { name: 'Security Incident', icon: '🛡️', color: '#EF4444' }
    ];

    // ─── Build HTML ──────────────────────────────────────────────────────────
    const totalDoctypes = DOCTYPE_GROUPS.reduce((acc, g) => acc + g.items.length, 0);
    const totalReports = REPORT_GROUPS.reduce((acc, g) => acc + g.items.length, 0);
    const totalDashboards = DASHBOARD_GROUPS.reduce((acc, g) => acc + g.items.length, 0);

    const html = `
        <div id="admin-shc-root">
            <!-- Top Bar -->
            <div class="admin-shc-top-bar">
                <div class="admin-shc-brand">
                    <span class="brand-icon">🏛️</span>
                    <span class="brand-name">Admin Shortcut</span>
                    <span class="brand-version">v2.0</span>
                    <span class="brand-badge">Ecclesia Admin</span>
                </div>
                <div class="admin-shc-controls">
                    <div class="admin-shc-theme-selector">
                        ${Object.entries(THEMES).map(([key, t]) => `
                            <button class="theme-btn ${key === currentTheme ? 'active' : ''}" 
                                    data-theme="${key}" title="${t.name}"
                                    style="background: ${t.primary};">
                                <span class="theme-dot" style="background: ${t.accent};"></span>
                            </button>
                        `).join('')}
                    </div>
                    <div class="admin-shc-search-wrapper">
                        <input type="text" id="admin-shc-search" placeholder="Search..." />
                        <span class="search-shortcut">⌘K</span>
                    </div>
                </div>
            </div>

            <!-- Stats Bar -->
            <div class="admin-shc-stats">
                <div class="stat-card"><span class="stat-icon">📋</span><span class="stat-number">${totalDoctypes}</span><span class="stat-label">Doctypes</span></div>
                <div class="stat-card"><span class="stat-icon">📊</span><span class="stat-number">${totalReports}</span><span class="stat-label">Reports</span></div>
                <div class="stat-card"><span class="stat-icon">📈</span><span class="stat-number">${totalDashboards}</span><span class="stat-label">Dashboards</span></div>
                <div class="stat-card"><span class="stat-icon">⭐</span><span class="stat-number" id="favorite-count">0</span><span class="stat-label">Favorites</span></div>
            </div>

            <!-- Daily Ops -->
            <div class="admin-shc-daily-ops">
                <span class="daily-ops-label">⭐ Daily Ops:</span>
                ${DAILY_OPS.map(item => `
                    <div class="daily-op-item" onclick="openAdminShortcut('List', '${item.name}')" style="--op-color: ${item.color}">
                        <span class="daily-op-icon">${item.icon}</span>
                        <span class="daily-op-name">${item.name}</span>
                    </div>
                `).join('')}
            </div>

            <!-- Vertical Layout: Sidebar + Content -->
            <div class="admin-shc-layout">
                <!-- Sidebar -->
                <div class="admin-shc-sidebar">
                    ${TABS.map(tab => `
                        <button class="admin-shc-sidebar-btn ${tab.id === 'doctypes' ? 'active' : ''}" 
                                data-tab="${tab.id}" title="${tab.label}">
                            <span class="sidebar-icon">${tab.icon}</span>
                            <span class="sidebar-label">${tab.label}</span>
                        </button>
                    `).join('')}
                </div>

                <!-- Content -->
                <div class="admin-shc-content">
                    <!-- Doctypes Tab -->
                    <div class="admin-shc-panel active" data-panel="doctypes">
                        <div class="panel-header">
                            <h2>📋 Doctypes</h2>
                            <span class="panel-count">${totalDoctypes} shortcuts</span>
                        </div>
                        <div class="panel-grid" id="doctype-grid"></div>
                    </div>

                    <!-- Reports Tab -->
                    <div class="admin-shc-panel" data-panel="reports">
                        <div class="panel-header">
                            <h2>📊 Reports</h2>
                            <span class="panel-count">${totalReports} reports</span>
                        </div>
                        <div class="panel-grid" id="report-grid"></div>
                    </div>

                    <!-- Dashboards Tab -->
                    <div class="admin-shc-panel" data-panel="dashboards">
                        <div class="panel-header">
                            <h2>📈 Dashboards</h2>
                            <span class="panel-count">${totalDashboards} dashboards</span>
                        </div>
                        <div class="panel-grid" id="dashboard-grid"></div>
                    </div>

                    <!-- Favorites Tab -->
                    <div class="admin-shc-panel" data-panel="favorites">
                        <div class="panel-header">
                            <h2>⭐ Favorites</h2>
                            <span class="panel-count" id="fav-count-display">0 items</span>
                        </div>
                        <div id="favorites-container"></div>
                    </div>
                </div>
            </div>
        </div>

        <style>
            /* ─── Base ─────────────────────────────────────────────────────────── */
            #admin-shc-root {
                padding: 16px 20px;
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background: var(--admin-shc-bg, #F8FAFC);
                color: var(--admin-shc-text, #0F172A);
                min-height: 100vh;
                transition: all 0.3s ease;
            }

            #admin-shc-root[data-theme="corporate"] {
                --admin-shc-primary: #1E293B; --admin-shc-accent: #3B82F6;
                --admin-shc-bg: #F8FAFC; --admin-shc-card: #FFFFFF;
                --admin-shc-text: #0F172A; --admin-shc-muted: #64748B;
                --admin-shc-border: #E2E8F0; --admin-shc-section-bg: rgba(59,130,246,0.04);
                --admin-shc-gradient: linear-gradient(135deg,#1E293B 0%,#3B82F6 100%);
                --admin-shc-sidebar-bg: #1E293B; --admin-shc-sidebar-text: #94A3B8;
                --admin-shc-sidebar-active: #3B82F6; --admin-shc-sidebar-hover: #334155;
            }
            #admin-shc-root[data-theme="emerald"] {
                --admin-shc-primary: #065F46; --admin-shc-accent: #34D399;
                --admin-shc-bg: #ECFDF5; --admin-shc-card: #FFFFFF;
                --admin-shc-text: #022C22; --admin-shc-muted: #047857;
                --admin-shc-border: #A7F3D0; --admin-shc-section-bg: rgba(5,150,105,0.06);
                --admin-shc-gradient: linear-gradient(135deg,#022C22 0%,#059669 50%,#34D399 100%);
                --admin-shc-sidebar-bg: #065F46; --admin-shc-sidebar-text: #86EFAC;
                --admin-shc-sidebar-active: #34D399; --admin-shc-sidebar-hover: #047857;
            }
            #admin-shc-root[data-theme="royal"] {
                --admin-shc-primary: #4C1D95; --admin-shc-accent: #A78BFA;
                --admin-shc-bg: #FAF5FF; --admin-shc-card: #FFFFFF;
                --admin-shc-text: #2E1065; --admin-shc-muted: #6D28D9;
                --admin-shc-border: #E9D5FF; --admin-shc-section-bg: rgba(124,58,237,0.06);
                --admin-shc-gradient: linear-gradient(135deg,#1E1B4B 0%,#7C3AED 50%,#A78BFA 100%);
                --admin-shc-sidebar-bg: #4C1D95; --admin-shc-sidebar-text: #C4B5FD;
                --admin-shc-sidebar-active: #A78BFA; --admin-shc-sidebar-hover: #6D28D9;
            }
            #admin-shc-root[data-theme="sunset"] {
                --admin-shc-primary: #9A3412; --admin-shc-accent: #F97316;
                --admin-shc-bg: #FFF7ED; --admin-shc-card: #FFFFFF;
                --admin-shc-text: #431407; --admin-shc-muted: #9A3412;
                --admin-shc-border: #FED7AA; --admin-shc-section-bg: rgba(234,88,12,0.06);
                --admin-shc-gradient: linear-gradient(135deg,#431407 0%,#EA580C 50%,#FBBF24 100%);
                --admin-shc-sidebar-bg: #9A3412; --admin-shc-sidebar-text: #FDBA74;
                --admin-shc-sidebar-active: #F97316; --admin-shc-sidebar-hover: #C2410C;
            }
            #admin-shc-root[data-theme="ocean"] {
                --admin-shc-primary: #0C4A6E; --admin-shc-accent: #38BDF8;
                --admin-shc-bg: #F0F9FF; --admin-shc-card: #FFFFFF;
                --admin-shc-text: #0C4A6E; --admin-shc-muted: #0369A1;
                --admin-shc-border: #BAE6FD; --admin-shc-section-bg: rgba(2,132,199,0.06);
                --admin-shc-gradient: linear-gradient(135deg,#0C4A6E 0%,#0284C7 50%,#38BDF8 100%);
                --admin-shc-sidebar-bg: #0C4A6E; --admin-shc-sidebar-text: #7DD3FC;
                --admin-shc-sidebar-active: #38BDF8; --admin-shc-sidebar-hover: #0369A1;
            }
            #admin-shc-root[data-theme="midnight"] {
                --admin-shc-primary: #0F172A; --admin-shc-accent: #818CF8;
                --admin-shc-bg: #0F172A; --admin-shc-card: #1E293B;
                --admin-shc-text: #F1F5F9; --admin-shc-muted: #94A3B8;
                --admin-shc-border: #334155; --admin-shc-section-bg: rgba(99,102,241,0.08);
                --admin-shc-gradient: linear-gradient(135deg,#020617 0%,#1E293B 50%,#6366F1 100%);
                --admin-shc-sidebar-bg: #0F172A; --admin-shc-sidebar-text: #94A3B8;
                --admin-shc-sidebar-active: #818CF8; --admin-shc-sidebar-hover: #1E293B;
            }
            #admin-shc-root[data-theme="forest"] {
                --admin-shc-primary: #052E16; --admin-shc-accent: #22C55E;
                --admin-shc-bg: #052E16; --admin-shc-card: #14532D;
                --admin-shc-text: #F0FDF4; --admin-shc-muted: #86EFAC;
                --admin-shc-border: #166534; --admin-shc-section-bg: rgba(34,197,94,0.08);
                --admin-shc-gradient: linear-gradient(135deg,#052E16 0%,#166534 50%,#22C55E 100%);
                --admin-shc-sidebar-bg: #052E16; --admin-shc-sidebar-text: #86EFAC;
                --admin-shc-sidebar-active: #22C55E; --admin-shc-sidebar-hover: #166534;
            }

            /* ─── Top Bar ──────────────────────────────────────────────────────── */
            .admin-shc-top-bar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 14px;
                flex-wrap: wrap;
                background: var(--admin-shc-card);
                padding: 10px 18px;
                border-radius: 14px;
                border: 1px solid var(--admin-shc-border);
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }
            .admin-shc-brand {
                display: flex;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
            }
            .brand-icon { font-size: 22px; }
            .brand-name {
                font-size: 17px;
                font-weight: 800;
                color: var(--admin-shc-text);
            }
            .brand-version {
                font-size: 10px;
                font-weight: 600;
                color: var(--admin-shc-muted);
                background: var(--admin-shc-bg);
                padding: 2px 8px;
                border-radius: 12px;
            }
            .brand-badge {
                font-size: 9px;
                font-weight: 700;
                color: #fff;
                background: var(--admin-shc-gradient);
                padding: 2px 12px;
                border-radius: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .admin-shc-controls {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }
            .admin-shc-theme-selector {
                display: flex;
                gap: 5px;
                align-items: center;
            }
            .theme-btn {
                width: 28px;
                height: 28px;
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
                border-color: var(--admin-shc-accent);
                box-shadow: 0 0 0 3px var(--admin-shc-accent)33;
            }
            .theme-dot { width: 13px; height: 13px; border-radius: 50%; display: block; }
            .admin-shc-search-wrapper {
                position: relative;
                display: flex;
                align-items: center;
            }
            .admin-shc-search-wrapper input {
                padding: 7px 14px;
                padding-right: 50px;
                border-radius: 20px;
                border: 1px solid var(--admin-shc-border);
                background: var(--admin-shc-bg);
                color: var(--admin-shc-text);
                font-size: 12px;
                min-width: 160px;
                transition: all 0.2s;
                outline: none;
            }
            .admin-shc-search-wrapper input:focus {
                border-color: var(--admin-shc-accent);
                box-shadow: 0 0 0 3px var(--admin-shc-accent)33;
            }
            .search-shortcut {
                position: absolute;
                right: 10px;
                font-size: 9px;
                color: var(--admin-shc-muted);
                background: var(--admin-shc-card);
                padding: 1px 6px;
                border-radius: 4px;
                border: 1px solid var(--admin-shc-border);
                font-weight: 600;
                opacity: 0.6;
            }

            /* ─── Stats ───────────────────────────────────────────────────────── */
            .admin-shc-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
                gap: 8px;
                margin-bottom: 14px;
            }
            .stat-card {
                background: var(--admin-shc-card);
                border: 1px solid var(--admin-shc-border);
                border-radius: 10px;
                padding: 10px 14px;
                display: flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                transition: all 0.2s;
            }
            .stat-card:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.06);
            }
            .stat-icon { font-size: 18px; }
            .stat-number {
                font-size: 18px;
                font-weight: 800;
                color: var(--admin-shc-text);
                font-feature-settings: "tnum";
            }
            .stat-label {
                font-size: 8px;
                font-weight: 500;
                color: var(--admin-shc-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            /* ─── Daily Ops ───────────────────────────────────────────────────── */
            .admin-shc-daily-ops {
                display: flex;
                align-items: center;
                gap: 5px;
                flex-wrap: wrap;
                padding: 6px 14px;
                background: var(--admin-shc-card);
                border-radius: 10px;
                border: 1px solid var(--admin-shc-border);
                margin-bottom: 14px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }
            .daily-ops-label {
                font-size: 10px;
                font-weight: 700;
                color: var(--admin-shc-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-right: 4px;
            }
            .daily-op-item {
                display: flex;
                align-items: center;
                gap: 3px;
                padding: 3px 10px;
                border-radius: 16px;
                cursor: pointer;
                transition: all 0.2s;
                background: var(--admin-shc-bg);
                border: 1px solid transparent;
                font-size: 10px;
                font-weight: 500;
                color: var(--admin-shc-text);
            }
            .daily-op-item:hover {
                border-color: var(--op-color, var(--admin-shc-accent));
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }
            .daily-op-icon { font-size: 12px; }

            /* ─── Vertical Layout ────────────────────────────────────────────── */
            .admin-shc-layout {
                display: flex;
                gap: 16px;
                min-height: 500px;
            }

            /* ─── Sidebar ─────────────────────────────────────────────────────── */
            .admin-shc-sidebar {
                width: 180px;
                min-width: 180px;
                background: var(--admin-shc-sidebar-bg);
                border-radius: 14px;
                padding: 8px 6px;
                display: flex;
                flex-direction: column;
                gap: 4px;
                border: 1px solid var(--admin-shc-border);
                height: fit-content;
                position: sticky;
                top: 16px;
            }
            .admin-shc-sidebar-btn {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px 14px;
                border: none;
                border-radius: 10px;
                background: transparent;
                color: var(--admin-shc-sidebar-text);
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                font-family: inherit;
                width: 100%;
                text-align: left;
            }
            .admin-shc-sidebar-btn:hover {
                background: var(--admin-shc-sidebar-hover);
                color: #fff;
            }
            .admin-shc-sidebar-btn.active {
                background: var(--admin-shc-sidebar-active);
                color: #fff;
                box-shadow: 0 2px 8px var(--admin-shc-sidebar-active)44;
            }
            .sidebar-icon { font-size: 16px; }
            .sidebar-label { flex: 1; }

            /* ─── Content ──────────────────────────────────────────────────────── */
            .admin-shc-content {
                flex: 1;
                min-width: 0;
            }
            .admin-shc-panel {
                display: none;
                animation: fadeIn 0.3s ease;
            }
            .admin-shc-panel.active { display: block; }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(6px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .panel-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 14px;
                padding: 0 4px;
            }
            .panel-header h2 {
                font-size: 18px;
                font-weight: 800;
                color: var(--admin-shc-text);
                margin: 0;
            }
            .panel-count {
                font-size: 12px;
                color: var(--admin-shc-muted);
                background: var(--admin-shc-bg);
                padding: 2px 12px;
                border-radius: 20px;
                font-weight: 600;
            }

            /* ─── 3-Column Grid ───────────────────────────────────────────────── */
            .panel-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 14px;
                align-items: start;
            }

            /* ─── Group Cards ─────────────────────────────────────────────────── */
            .admin-shc-group {
                background: var(--admin-shc-card);
                border-radius: 12px;
                border: 1px solid var(--admin-shc-border);
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                transition: all 0.2s;
                display: flex;
                flex-direction: column;
            }
            .admin-shc-group:hover {
                box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            }
            .admin-shc-group-header {
                padding: 8px 14px;
                background: var(--admin-shc-section-bg);
                border-bottom: 3px solid var(--group-color, var(--admin-shc-accent));
                display: flex;
                align-items: center;
                gap: 8px;
                flex-shrink: 0;
            }
            .group-icon { font-size: 15px; }
            .group-name {
                font-weight: 700;
                font-size: 12px;
                color: var(--admin-shc-text);
                flex: 1;
            }
            .group-count {
                font-size: 9px;
                font-weight: 600;
                color: var(--admin-shc-muted);
                background: var(--admin-shc-bg);
                padding: 1px 7px;
                border-radius: 10px;
            }
            .admin-shc-group-body {
                padding: 6px 10px 10px;
                display: flex;
                flex-direction: column;
                gap: 2px;
                flex: 1;
            }

            /* ─── Items ───────────────────────────────────────────────────────── */
            .admin-shc-item {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 4px 10px;
                border-radius: 6px;
                background: var(--admin-shc-bg);
                border: 1px solid transparent;
                cursor: pointer;
                transition: all 0.15s;
                position: relative;
            }
            .admin-shc-item:hover {
                border-color: var(--admin-shc-accent);
                transform: translateX(3px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            }
            .admin-shc-item .fav-btn {
                background: none;
                border: none;
                cursor: pointer;
                font-size: 10px;
                opacity: 0.2;
                transition: all 0.2s;
                padding: 0 2px;
                color: var(--admin-shc-text);
            }
            .admin-shc-item .fav-btn:hover { opacity: 1; transform: scale(1.2); }
            .admin-shc-item .fav-btn.active { opacity: 1; color: #F59E0B; }
            .admin-shc-item-icon {
                width: 24px;
                height: 24px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                flex-shrink: 0;
            }
            .admin-shc-item-name {
                font-size: 10.5px;
                font-weight: 500;
                color: var(--admin-shc-text);
                line-height: 1.3;
                flex: 1;
            }
            .admin-shc-item-desc {
                font-size: 8.5px;
                color: var(--admin-shc-muted);
                opacity: 0.6;
            }
            .admin-shc-item .open-indicator {
                font-size: 8px;
                color: var(--admin-shc-muted);
                opacity: 0.3;
                transition: opacity 0.2s;
            }
            .admin-shc-item:hover .open-indicator { opacity: 1; }

            /* ─── Dashboard Cards ────────────────────────────────────────────── */
            .admin-shc-dashboard-item {
                background: var(--admin-shc-bg);
                border: 1px solid var(--admin-shc-border);
                border-radius: 10px;
                padding: 12px 14px;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 12px;
                position: relative;
            }
            .admin-shc-dashboard-item:hover {
                border-color: var(--admin-shc-accent);
                transform: translateY(-2px);
                box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            }
            .admin-shc-dashboard-item .fav-btn {
                position: absolute;
                top: 4px;
                right: 6px;
                background: none;
                border: none;
                cursor: pointer;
                font-size: 11px;
                opacity: 0.2;
                transition: all 0.2s;
                padding: 2px 4px;
            }
            .admin-shc-dashboard-item .fav-btn:hover { opacity: 1; transform: scale(1.2); }
            .admin-shc-dashboard-item .fav-btn.active { opacity: 1; color: #F59E0B; }
            .dashboard-item-icon { font-size: 24px; flex-shrink: 0; }
            .dashboard-item-info { flex: 1; }
            .dashboard-item-name {
                font-size: 12px;
                font-weight: 700;
                color: var(--admin-shc-text);
                display: block;
            }
            .dashboard-item-desc {
                font-size: 10px;
                color: var(--admin-shc-muted);
                display: block;
            }
            .dashboard-item-badge {
                font-size: 8px;
                font-weight: 600;
                padding: 1px 8px;
                border-radius: 8px;
                background: var(--admin-shc-primary)22;
                color: var(--admin-shc-primary);
            }

            /* ─── Favorites ───────────────────────────────────────────────────── */
            #favorites-container { min-height: 120px; }
            .empty-state {
                text-align: center;
                padding: 40px 20px;
                background: var(--admin-shc-card);
                border-radius: 14px;
                border: 2px dashed var(--admin-shc-border);
            }
            .empty-icon { font-size: 36px; margin-bottom: 8px; }
            .empty-state h3 {
                font-size: 15px;
                color: var(--admin-shc-text);
                margin: 0 0 4px 0;
            }
            .empty-state p {
                color: var(--admin-shc-muted);
                font-size: 12px;
                margin: 0;
            }

            /* ─── Responsive ──────────────────────────────────────────────────── */
            @media (max-width: 1200px) {
                .panel-grid { grid-template-columns: repeat(2, 1fr); }
            }
            @media (max-width: 992px) {
                .admin-shc-sidebar { width: 60px; min-width: 60px; }
                .sidebar-label { display: none; }
                .admin-shc-sidebar-btn { justify-content: center; padding: 12px; }
            }
            @media (max-width: 768px) {
                #admin-shc-root { padding: 12px; }
                .admin-shc-layout { flex-direction: column; }
                .admin-shc-sidebar {
                    width: 100%;
                    min-width: unset;
                    flex-direction: row;
                    padding: 4px 6px;
                    position: static;
                    overflow-x: auto;
                }
                .admin-shc-sidebar-btn {
                    flex: 1;
                    justify-content: center;
                    padding: 8px 12px;
                    min-width: 60px;
                }
                .sidebar-label { display: inline; font-size: 10px; }
                .panel-grid { grid-template-columns: 1fr; }
                .admin-shc-top-bar { flex-direction: column; align-items: stretch; }
                .admin-shc-controls { flex-wrap: wrap; }
                .admin-shc-search-wrapper input { min-width: 100%; }
                .admin-shc-stats { grid-template-columns: 1fr 1fr; }
                .admin-shc-daily-ops { gap: 4px; }
                .daily-op-item { font-size: 9px; padding: 2px 8px; }
            }
            @media (max-width: 480px) {
                .admin-shc-stats { grid-template-columns: 1fr; }
                .admin-shc-sidebar-btn { padding: 6px 8px; min-width: 50px; }
                .sidebar-label { font-size: 8px; }
            }
        </style>
    `;

    // ─── Inject HTML ──────────────────────────────────────────────────────────
    $(page.main).append(html);

    // ─── Initialize ──────────────────────────────────────────────────────────
    const root = document.getElementById('admin-shc-root');
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
        } else if (type === 'Page') {
            return `/app/${name}`;
        } else {
            return `/app/${name}`;
        }
    }

    // ─── Render Helper: Create Group HTML ──────────────────────────────────
    function renderGroup(group, type, favorites) {
        const isFav = (name) => favorites.includes(name);
        const groupClass = type === 'dashboard' ? 'admin-shc-dashboard-item' : 'admin-shc-item';
        if (type === 'dashboard') {
            return `
                <div class="admin-shc-group">
                    <div class="admin-shc-group-header" style="border-color: ${group.color};">
                        <span class="group-icon">${group.icon}</span>
                        <span class="group-name">${group.name}</span>
                        <span class="group-count">${group.items.length}</span>
                    </div>
                    <div class="admin-shc-group-body">
                        ${group.items.map(item => `
                            <div class="${groupClass}" onclick="openAdminShortcut('Page', '${item.name}')">
                                <button class="fav-btn ${isFav(item.name) ? 'active' : ''}" 
                                        onclick="event.stopPropagation(); toggleFavorite('${item.name}')">
                                    ${isFav(item.name) ? '⭐' : '☆'}
                                </button>
                                <span class="dashboard-item-icon">${item.icon}</span>
                                <div class="dashboard-item-info">
                                    <span class="dashboard-item-name">${item.name}</span>
                                    <span class="dashboard-item-desc">${item.desc || ''}</span>
                                </div>
                                <span class="dashboard-item-badge" style="background:${item.color}22;color:${item.color}">Launch</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="admin-shc-group">
                    <div class="admin-shc-group-header" style="border-color: ${group.color};">
                        <span class="group-icon">${group.icon}</span>
                        <span class="group-name">${group.name}</span>
                        <span class="group-count">${group.items.length}</span>
                    </div>
                    <div class="admin-shc-group-body">
                        ${group.items.map(item => {
                            const fav = isFav(item.name);
                            const color = item.color || '#8B5CF6';
                            return `
                                <div class="${groupClass}" onclick="openAdminShortcut('${type === 'report' ? 'Report' : 'List'}', '${item.name}')">
                                    <button class="fav-btn ${fav ? 'active' : ''}" 
                                            onclick="event.stopPropagation(); toggleFavorite('${item.name}')">
                                        ${fav ? '⭐' : '☆'}
                                    </button>
                                    <div class="admin-shc-item-icon" style="background:${color}22;color:${color}">${item.icon}</div>
                                    <span class="admin-shc-item-name">${item.name}</span>
                                    <span class="open-indicator">↗</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }
    }

    // ─── Render Doctype Grid ──────────────────────────────────────────────────
    function renderDoctypeGrid(filter = '') {
        const container = document.getElementById('doctype-grid');
        const favorites = JSON.parse(localStorage.getItem('admin_shc_favorites') || '[]');

        let html = '';
        DOCTYPE_GROUPS.forEach(group => {
            const filtered = group.items.filter(item =>
                item.name.toLowerCase().includes(filter.toLowerCase()) ||
                group.name.toLowerCase().includes(filter.toLowerCase())
            );
            if (filtered.length === 0) return;
            const filteredGroup = { ...group, items: filtered };
            html += renderGroup(filteredGroup, 'doctype', favorites);
        });

        container.innerHTML = html || '<div class="empty-state"><div class="empty-icon">🔍</div><h3>No doctypes found</h3><p>Try adjusting your search</p></div>';
    }

    // ─── Render Report Grid ────────────────────────────────────────────────────
    function renderReportGrid(filter = '') {
        const container = document.getElementById('report-grid');
        const favorites = JSON.parse(localStorage.getItem('admin_shc_favorites') || '[]');

        let html = '';
        REPORT_GROUPS.forEach(group => {
            const filtered = group.items.filter(item =>
                item.name.toLowerCase().includes(filter.toLowerCase()) ||
                group.name.toLowerCase().includes(filter.toLowerCase())
            );
            if (filtered.length === 0) return;
            const filteredGroup = { ...group, items: filtered };
            html += renderGroup(filteredGroup, 'report', favorites);
        });

        container.innerHTML = html || '<div class="empty-state"><div class="empty-icon">🔍</div><h3>No reports found</h3><p>Try adjusting your search</p></div>';
    }

    // ─── Render Dashboard Grid ──────────────────────────────────────────────────
    function renderDashboardGrid(filter = '') {
        const container = document.getElementById('dashboard-grid');
        const favorites = JSON.parse(localStorage.getItem('admin_shc_favorites') || '[]');

        let html = '';
        DASHBOARD_GROUPS.forEach(group => {
            const filtered = group.items.filter(item =>
                item.name.toLowerCase().includes(filter.toLowerCase()) ||
                (item.desc && item.desc.toLowerCase().includes(filter.toLowerCase())) ||
                group.name.toLowerCase().includes(filter.toLowerCase())
            );
            if (filtered.length === 0) return;
            const filteredGroup = { ...group, items: filtered };
            html += renderGroup(filteredGroup, 'dashboard', favorites);
        });

        container.innerHTML = html || '<div class="empty-state"><div class="empty-icon">🔍</div><h3>No dashboards found</h3><p>Try adjusting your search</p></div>';
    }

    // ─── Render Favorites ────────────────────────────────────────────────────
    function renderFavorites() {
        const container = document.getElementById('favorites-container');
        const favorites = JSON.parse(localStorage.getItem('admin_shc_favorites') || '[]');

        if (favorites.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⭐</div>
                    <h3>No favorites yet</h3>
                    <p>Click the star icon on any item to save it here</p>
                </div>
            `;
            document.getElementById('fav-count-display').textContent = '0 items';
            return;
        }

        // Collect all items
        const allItems = [];
        DOCTYPE_GROUPS.forEach(g => g.items.forEach(item => allItems.push({ ...item, type: 'List', section: g.name })));
        REPORT_GROUPS.forEach(g => g.items.forEach(item => allItems.push({ ...item, type: 'Report', section: g.name })));
        DASHBOARD_GROUPS.forEach(g => g.items.forEach(item => allItems.push({ ...item, type: 'Page', section: g.name })));

        const favItems = allItems.filter(item => favorites.includes(item.name));

        document.getElementById('fav-count-display').textContent = `${favItems.length} items`;

        if (favItems.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⭐</div>
                    <h3>No favorites found</h3>
                    <p>Your saved items will appear here</p>
                </div>
            `;
            return;
        }

        // Group favorites by section
        const grouped = {};
        favItems.forEach(item => {
            const section = item.section || 'Other';
            if (!grouped[section]) grouped[section] = [];
            grouped[section].push(item);
        });

        let html = '';
        Object.entries(grouped).forEach(([section, items]) => {
            html += `
                <div class="admin-shc-group">
                    <div class="admin-shc-group-header" style="border-color: var(--admin-shc-accent);">
                        <span class="group-icon">⭐</span>
                        <span class="group-name">${section}</span>
                        <span class="group-count">${items.length}</span>
                    </div>
                    <div class="admin-shc-group-body">
                        ${items.map(item => {
                            const color = item.color || '#8B5CF6';
                            const type = item.type || 'List';
                            return `
                                <div class="admin-shc-item" onclick="openAdminShortcut('${type}', '${item.name}')">
                                    <button class="fav-btn active" onclick="event.stopPropagation(); toggleFavorite('${item.name}')">⭐</button>
                                    <div class="admin-shc-item-icon" style="background:${color}22;color:${color}">${item.icon}</div>
                                    <span class="admin-shc-item-name">${item.name}</span>
                                    <span style="font-size:7px;color:var(--admin-shc-muted);opacity:0.5;text-transform:uppercase;">${type}</span>
                                    <span class="open-indicator">↗</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    // ─── Toggle Favorite ────────────────────────────────────────────────────
    window.toggleFavorite = function(id) {
        let favorites = JSON.parse(localStorage.getItem('admin_shc_favorites') || '[]');
        const index = favorites.indexOf(id);
        if (index > -1) {
            favorites.splice(index, 1);
        } else {
            favorites.push(id);
        }
        localStorage.setItem('admin_shc_favorites', JSON.stringify(favorites));

        const searchVal = document.getElementById('admin-shc-search').value;
        const activeTab = document.querySelector('.admin-shc-sidebar-btn.active').dataset.tab;

        if (activeTab === 'doctypes') renderDoctypeGrid(searchVal);
        else if (activeTab === 'reports') renderReportGrid(searchVal);
        else if (activeTab === 'dashboards') renderDashboardGrid(searchVal);
        else if (activeTab === 'favorites') renderFavorites();

        updateStats();
    };

    // ─── Open Admin Shortcut ──────────────────────────────────────────────────
    window.openAdminShortcut = function(type, name) {
        const url = getRoute(type, name);
        openInNewTab(url);
    };

    // ─── Update Stats ───────────────────────────────────────────────────────
    function updateStats() {
        const favorites = JSON.parse(localStorage.getItem('admin_shc_favorites') || '[]');
        document.getElementById('favorite-count').textContent = favorites.length;
        if (document.getElementById('fav-count-display')) {
            document.getElementById('fav-count-display').textContent = `${favorites.length} items`;
        }
    }

    // ─── Sidebar Tab Switching ──────────────────────────────────────────────
    document.querySelectorAll('.admin-shc-sidebar-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.admin-shc-sidebar-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const panelId = this.dataset.tab;
            document.querySelectorAll('.admin-shc-panel').forEach(p => p.classList.remove('active'));
            document.querySelector(`.admin-shc-panel[data-panel="${panelId}"]`).classList.add('active');

            const searchVal = document.getElementById('admin-shc-search').value;
            if (panelId === 'doctypes') renderDoctypeGrid(searchVal);
            else if (panelId === 'reports') renderReportGrid(searchVal);
            else if (panelId === 'dashboards') renderDashboardGrid(searchVal);
            else if (panelId === 'favorites') renderFavorites();
        });
    });

    // ─── Theme Switching ────────────────────────────────────────────────────
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const theme = this.dataset.theme;
            root.dataset.theme = theme;
            localStorage.setItem('admin_shc_theme', theme);
            document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentTheme = theme;
        });
    });

    // ─── Search ─────────────────────────────────────────────────────────────
    document.getElementById('admin-shc-search').addEventListener('input', function() {
        const val = this.value;
        const activeTab = document.querySelector('.admin-shc-sidebar-btn.active').dataset.tab;
        if (activeTab === 'doctypes') renderDoctypeGrid(val);
        else if (activeTab === 'reports') renderReportGrid(val);
        else if (activeTab === 'dashboards') renderDashboardGrid(val);
    });

    // ─── Keyboard Shortcuts ──────────────────────────────────────────────────
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('admin-shc-search').focus();
        }
        if (e.key === 'Escape') {
            document.getElementById('admin-shc-search').blur();
        }
    });

    // ─── Initial Render ─────────────────────────────────────────────────────
    renderDoctypeGrid('');
    renderReportGrid('');
    renderDashboardGrid('');
    renderFavorites();
    updateStats();

    // ─── Expose for debugging ──────────────────────────────────────────────
    window.adminShortcut = {
        DOCTYPE_GROUPS,
        REPORT_GROUPS,
        DASHBOARD_GROUPS,
        DAILY_OPS,
        THEMES,
        openAdminShortcut,
        toggleFavorite
    };
};