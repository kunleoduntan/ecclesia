// ecclesia/ecclesia/page/hr-shc/hr-shc.js
// HR-SHC — "Hearts & Records" HR Command Center
// ERPNext HR Module + Ecclesia HR/Payroll/Compliance, presentation-friendly cute theme

frappe.pages['hr-shc'] = frappe.pages['hr-shc'] || {};

frappe.pages['hr-shc'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '💗 HR-SHC · Hearts & Records',
        single_column: true
    });

    // ─── 11 GROUPS — ERPNext HR core + Ecclesia HR/Payroll/Compliance ──────
    const GROUPS = [
        {
            id: 'people',
            name: '🧑‍🤝‍🧑 People & Org',
            icon: '🧑‍🤝‍🧑',
            color: '#FB7185',
            items: [
                { name: 'Employee', icon: '🪪', color: '#FB7185' },
                { name: 'Employee Document', icon: '📁', color: '#F472B6' },
                { name: 'Department', icon: '🏷️', color: '#FB923C' },
                { name: 'Designation', icon: '🎀', color: '#F59E0B' },
                { name: 'Branch', icon: '🌿', color: '#34D399' },
                { name: 'Employee Grade', icon: '🌟', color: '#FBBF24' },
                { name: 'Employee Group', icon: '👯', color: '#A78BFA' },
                { name: 'Holiday List', icon: '🎈', color: '#60A5FA' }
            ]
        },
        {
            id: 'attendance',
            name: '⏰ Attendance & Leave',
            icon: '⏰',
            color: '#60A5FA',
            items: [
                { name: 'Attendance', icon: '✅', color: '#34D399' },
                { name: 'Employee Attendance Tool', icon: '🧮', color: '#22D3EE' },
                { name: 'Shift Type', icon: '🌙', color: '#818CF8' },
                { name: 'Shift Assignment', icon: '📌', color: '#60A5FA' },
                { name: 'Leave Application', icon: '🌴', color: '#34D399' },
                { name: 'Leave Type', icon: '🍃', color: '#10B981' },
                { name: 'Leave Policy', icon: '📘', color: '#6366F1' },
                { name: 'Leave Policy Assignment', icon: '📑', color: '#7C3AED' },
                { name: 'Leave Allocation', icon: '🎁', color: '#F472B6' },
                { name: 'Compensatory Leave Request', icon: '🔁', color: '#FB923C' },
                { name: 'Leave Block List', icon: '🚫', color: '#EF4444' }
            ]
        },
        {
            id: 'recruitment',
            name: '🌸 Recruitment & Onboarding',
            icon: '🌸',
            color: '#F472B6',
            items: [
                { name: 'Job Opening', icon: '📣', color: '#FB7185' },
                { name: 'Job Applicant', icon: '🙋', color: '#F472B6' },
                { name: 'Interview Round', icon: '🎙️', color: '#A78BFA' },
                { name: 'Interview', icon: '🗣️', color: '#8B5CF6' },
                { name: 'Job Offer', icon: '🎉', color: '#FBBF24' },
                { name: 'Staffing Plan', icon: '🗺️', color: '#34D399' },
                { name: 'Employee Onboarding', icon: '🌱', color: '#22C55E' },
                { name: 'Employee Boarding Activity', icon: '🧩', color: '#06B6D4' },
                { name: 'Employee Separation', icon: '👋', color: '#F87171' },
                { name: 'Employee Transfer', icon: '🔄', color: '#60A5FA' },
                { name: 'Employee Promotion', icon: '🚀', color: '#FB923C' }
            ]
        },
        {
            id: 'payroll',
            name: '💰 Payroll & Compensation',
            icon: '💰',
            color: '#34D399',
            items: [
                { name: 'Salary Structure', icon: '🧱', color: '#34D399' },
                { name: 'Salary Structure Assignment', icon: '📎', color: '#10B981' },
                { name: 'Salary Component', icon: '🧮', color: '#22C55E' },
                { name: 'Salary Slip', icon: '🧾', color: '#0EA5E9' },
                { name: 'Payroll Entry', icon: '📤', color: '#3B82F6' },
                { name: 'Payroll Period', icon: '📆', color: '#6366F1' },
                { name: 'Additional Salary', icon: '➕', color: '#F59E0B' },
                { name: 'Employee Incentive', icon: '🏅', color: '#FBBF24' },
                { name: 'Retention Bonus', icon: '🎯', color: '#F472B6' },
                { name: 'Gratuity', icon: '🎁', color: '#FB7185' },
                { name: 'Income Tax Slab', icon: '📊', color: '#A78BFA' },
                { name: 'Employee Tax Exemption Declaration', icon: '📝', color: '#8B5CF6' },
                { name: 'Employee Tax Exemption Proof Submission', icon: '📎', color: '#7C3AED' }
            ]
        },
        {
            id: 'loans',
            name: '💳 Loans & Advances',
            icon: '💳',
            color: '#FBBF24',
            items: [
                { name: 'Employee Loan Application', icon: '📋', color: '#059669' },
                { name: 'Loan Application', icon: '📄', color: '#0284C7' },
                { name: 'Loan', icon: '🏦', color: '#16A34A' },
                { name: 'Loan Type', icon: '🗂️', color: '#65A30D' },
                { name: 'Loan Repayment Entry', icon: '💵', color: '#0EA5E9' },
                { name: 'Staff Loan Payment', icon: '💸', color: '#10B981' },
                { name: 'Employee Advance', icon: '🪙', color: '#F59E0B' },
                { name: 'Expense Claim', icon: '🧾', color: '#EF4444' },
                { name: 'Expense Claim Type', icon: '📂', color: '#F87171' },
                { name: 'Travel Request', icon: '✈️', color: '#38BDF8' }
            ]
        },
        {
            id: 'performance',
            name: '⭐ Performance & Growth',
            icon: '⭐',
            color: '#FBBF24',
            items: [
                { name: 'Appraisal', icon: '📈', color: '#F59E0B' },
                { name: 'Appraisal Cycle', icon: '🔄', color: '#FB923C' },
                { name: 'Appraisal Template', icon: '🧾', color: '#D97706' },
                { name: 'Goal', icon: '🎯', color: '#EF4444' },
                { name: 'Performance Cycle', icon: '🔁', color: '#8B5CF6' },
                { name: 'Employee Performance Record', icon: '🏆', color: '#A78BFA' },
                { name: 'Training Program', icon: '📚', color: '#34D399' },
                { name: 'Training Event', icon: '🎓', color: '#10B981' },
                { name: 'Training Result', icon: '✅', color: '#22C55E' },
                { name: 'Training Feedback', icon: '💬', color: '#06B6D4' }
            ]
        },
        {
            id: 'selfservice',
            name: '💌 Self-Service & Wellbeing',
            icon: '💌',
            color: '#F472B6',
            items: [
                { name: 'ESS Task', icon: '✅', color: '#5B21B6' },
                { name: 'ESS Activity Log', icon: '📋', color: '#7C3AED' },
                { name: 'Handover Notes', icon: '🤲', color: '#FB7185' },
                { name: 'Company Policy', icon: '📜', color: '#7C3AED' },
                { name: 'Policy Acknowledgement', icon: '✍️', color: '#10B981' },
                { name: 'Employee Grievance', icon: '💭', color: '#F87171' },
                { name: 'WFH Request', icon: '🏠', color: '#F97316' },
                { name: 'WFH Schedule', icon: '🗓️', color: '#F59E0B' },
                { name: 'WFH Session', icon: '🖥️', color: '#D97706' },
                { name: 'WFH Daily Summary', icon: '📊', color: '#EA580C' },
                { name: 'Work Session', icon: '💻', color: '#059669' },
                { name: 'Work Activity Log', icon: '📝', color: '#6B7280' }
            ]
        },
        {
            id: 'statutory',
            name: '📋 Statutory & Compliance',
            icon: '📋',
            color: '#A78BFA',
            items: [
                { name: 'Pension Remittance Batch', icon: '🏦', color: '#059669' },
                { name: 'Pension Manager', icon: '👤', color: '#0D9488' },
                { name: 'NHF Remittance Batch', icon: '🏠', color: '#D97706' },
                { name: 'NSITF Assessment', icon: '🛡️', color: '#EF4444' },
                { name: 'ITF Assessment', icon: '📊', color: '#F59E0B' },
                { name: 'Employee Tax Computation', icon: '🧾', color: '#DC2626' },
                { name: 'Compliance Filing', icon: '📄', color: '#3B82F6' },
                { name: 'Compliance Calendar', icon: '📅', color: '#7C3AED' },
                { name: 'Compliance Task', icon: '✅', color: '#22C55E' }
            ]
        },
        {
            id: 'settings',
            name: '⚙️ HR Settings & Structure',
            icon: '⚙️',
            color: '#94A3B8',
            items: [
                { name: 'HR Settings', icon: '⚙️', color: '#64748B' },
                { name: 'Daily Work Summary Group', icon: '🗒️', color: '#475569' },
                { name: 'Employee Health Insurance', icon: '➕', color: '#EF4444' },
                { name: 'Employee External Work History', icon: '🧳', color: '#0EA5E9' },
                { name: 'Employee Skill Map', icon: '🧠', color: '#A78BFA' },
                { name: 'Energy Point Rule', icon: '✨', color: '#FBBF24' }
            ]
        },
        {
            id: 'dashboards',
            name: '📊 Dashboards & Portals',
            icon: '📊',
            color: '#38BDF8',
            items: [
                { name: 'Employee Self Service', icon: '🌷', color: '#F472B6', route: '/app/employee-self-service' },
                { name: 'ComplianceHQ', icon: '🛡️', color: '#7C3AED', route: '/app/compliancehq' },
                { name: 'Church CRM 360', icon: '⛪', color: '#A78BFA', route: '/app/churchcrm360' },
                { name: 'Compliance KPI Snapshot', icon: '📈', color: '#059669' },
                { name: 'Employee Performance Record', icon: '🏆', color: '#F59E0B' }
            ]
        },
        {
            id: 'reports',
            name: '📑 HR & Payroll Reports',
            icon: '📑',
            color: '#FB923C',
            items: [
                { name: 'Monthly Attendance Sheet', icon: '🗓️', color: '#0EA5E9' },
                { name: 'Salary Register', icon: '💰', color: '#34D399' },
                { name: 'Employee Leave Balance', icon: '🌴', color: '#22C55E' },
                { name: 'Vehicle/Asset Allocation', icon: '🚗', color: '#F59E0B' },
                { name: 'Income Tax Computation', icon: '🧮', color: '#A78BFA' }
            ]
        }
    ];

    const totalItems = GROUPS.reduce((acc, g) => acc + g.items.length, 0);

    const html = `
        <div id="hr-shc-root">
            <div class="hr-shc-hero">
                <div class="hr-shc-hero-sparkles">🎀 ✨ 💗 ✨ 🎀</div>
                <h1>Hearts &amp; Records</h1>
                <p>Every people, payroll &amp; compliance shortcut in one cozy place</p>
                <div class="hr-shc-search-wrapper">
                    <span class="search-icon">🔎</span>
                    <input type="text" id="hr-shc-search" placeholder="Find a shortcut..." />
                </div>
            </div>

            <div class="hr-shc-stats">
                <div class="stat-pill"><span>📂</span> ${GROUPS.length} groups</div>
                <div class="stat-pill"><span>📋</span> ${totalItems} shortcuts</div>
                <div class="stat-pill"><span>⭐</span> <span id="favorite-count">0</span> favorites</div>
            </div>

            <div class="hr-shc-grid" id="hr-shc-grid">
                ${GROUPS.map(group => `
                    <div class="hr-shc-group" data-group="${group.id}" style="--group-color:${group.color}">
                        <div class="hr-shc-group-header">
                            <span class="group-icon">${group.icon}</span>
                            <span class="group-name">${group.name}</span>
                            <span class="group-count">${group.items.length}</span>
                        </div>
                        <div class="hr-shc-group-body">
                            ${group.items.map(item => `
                                <div class="hr-shc-item"
                                     onclick="openHrItem('${item.route || ''}', '${item.name}')"
                                     data-name="${item.name}">
                                    <button class="fav-btn" onclick="event.stopPropagation(); toggleHrFavorite('${item.name}')">♡</button>
                                    <div class="hr-shc-item-icon" style="background:${item.color}22;color:${item.color}">
                                        ${item.icon}
                                    </div>
                                    <span class="hr-shc-item-name">${item.name}</span>
                                    <span class="open-indicator">↗</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>

            <div class="hr-shc-empty" id="hr-shc-empty" style="display:none;">
                <div class="empty-icon">🧸</div>
                <h3>No shortcuts match that</h3>
                <p>Try a different search term</p>
            </div>

            <div class="hr-shc-footer">made with 💗 for the HR team</div>
        </div>

        <style>
            #hr-shc-root {
                --pink: #FFE4EC;
                --blush: #FB7185;
                --lavender: #EDE9FE;
                --mint: #D1FAE5;
                --cream: #FFFBF5;
                --text: #4A2C3A;
                --muted: #9B7B8C;
                --card: #FFFFFF;
                --border: #FBCFE8;
                font-family: 'Quicksand', 'Poppins', system-ui, -apple-system, sans-serif;
                background: linear-gradient(180deg, var(--cream) 0%, var(--pink) 100%);
                color: var(--text);
                padding: 20px 22px 40px;
                min-height: 100vh;
            }

            .hr-shc-hero {
                text-align: center;
                padding: 28px 16px 22px;
                margin-bottom: 18px;
                border-radius: 28px;
                background: linear-gradient(135deg, #FFD9E6 0%, #FFE9C7 50%, #E0D4FB 100%);
                box-shadow: 0 8px 24px rgba(251,113,133,0.18);
                position: relative;
                overflow: hidden;
            }
            .hr-shc-hero-sparkles {
                font-size: 14px;
                letter-spacing: 6px;
                opacity: 0.8;
                margin-bottom: 6px;
            }
            .hr-shc-hero h1 {
                font-size: 30px;
                font-weight: 800;
                margin: 0 0 4px;
                color: #9D174D;
                letter-spacing: 0.3px;
            }
            .hr-shc-hero p {
                margin: 0 0 16px;
                color: var(--muted);
                font-size: 13px;
                font-weight: 600;
            }
            .hr-shc-search-wrapper {
                max-width: 360px;
                margin: 0 auto;
                background: #fff;
                border-radius: 999px;
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 10px 18px;
                box-shadow: 0 4px 14px rgba(157,23,77,0.12);
                border: 2px solid #FFFFFF;
            }
            .hr-shc-search-wrapper input {
                border: none;
                outline: none;
                background: transparent;
                font-size: 14px;
                font-weight: 600;
                color: var(--text);
                width: 100%;
                font-family: inherit;
            }
            .hr-shc-search-wrapper input::placeholder { color: #D8A8BD; }

            .hr-shc-stats {
                display: flex;
                justify-content: center;
                gap: 10px;
                flex-wrap: wrap;
                margin-bottom: 20px;
            }
            .stat-pill {
                background: #fff;
                border-radius: 999px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 700;
                color: var(--blush);
                box-shadow: 0 2px 8px rgba(251,113,133,0.14);
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .hr-shc-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                align-items: start;
            }
            .hr-shc-group {
                background: var(--card);
                border-radius: 22px;
                border: 2px solid var(--border);
                overflow: hidden;
                box-shadow: 0 4px 16px rgba(251,113,133,0.10);
                transition: transform 0.18s ease, box-shadow 0.18s ease;
                display: flex;
                flex-direction: column;
            }
            .hr-shc-group:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 24px rgba(251,113,133,0.20);
            }
            .hr-shc-group-header {
                padding: 12px 14px;
                background: color-mix(in srgb, var(--group-color) 12%, white);
                border-bottom: 3px dashed var(--group-color);
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .group-icon { font-size: 17px; }
            .group-name {
                font-weight: 800;
                font-size: 13px;
                color: var(--text);
                flex: 1;
            }
            .group-count {
                font-size: 10px;
                font-weight: 800;
                color: #fff;
                background: var(--group-color);
                padding: 2px 9px;
                border-radius: 999px;
            }
            .hr-shc-group-body {
                padding: 8px 10px 12px;
                display: flex;
                flex-direction: column;
                gap: 4px;
                flex: 1;
            }

            .hr-shc-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 10px;
                border-radius: 14px;
                background: #FFF8FB;
                border: 1px solid transparent;
                cursor: pointer;
                transition: all 0.15s;
            }
            .hr-shc-item:hover {
                border-color: var(--group-color, var(--blush));
                background: #fff;
                transform: translateX(3px);
            }
            .hr-shc-item .fav-btn {
                background: none;
                border: none;
                cursor: pointer;
                font-size: 13px;
                opacity: 0.35;
                transition: all 0.2s;
                color: var(--blush);
                padding: 0 2px;
            }
            .hr-shc-item .fav-btn:hover { opacity: 1; transform: scale(1.2); }
            .hr-shc-item .fav-btn.active { opacity: 1; }
            .hr-shc-item-icon {
                width: 26px;
                height: 26px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                flex-shrink: 0;
            }
            .hr-shc-item-name {
                font-size: 11.5px;
                font-weight: 600;
                color: var(--text);
                line-height: 1.3;
                flex: 1;
            }
            .hr-shc-item .open-indicator {
                font-size: 9px;
                color: var(--muted);
                opacity: 0.3;
            }
            .hr-shc-item:hover .open-indicator { opacity: 1; }

            .hr-shc-empty {
                text-align: center;
                padding: 50px 20px;
                background: var(--card);
                border-radius: 22px;
                border: 2px dashed var(--border);
            }
            .empty-icon { font-size: 44px; margin-bottom: 10px; }
            .hr-shc-empty h3 { margin: 0 0 6px; color: var(--text); }
            .hr-shc-empty p { margin: 0; color: var(--muted); font-size: 13px; }

            .hr-shc-footer {
                text-align: center;
                margin-top: 24px;
                font-size: 12px;
                color: var(--muted);
                font-weight: 600;
            }

            @media (max-width: 1200px) { .hr-shc-grid { grid-template-columns: repeat(2, 1fr); } }
            @media (max-width: 768px) {
                #hr-shc-root { padding: 14px; }
                .hr-shc-grid { grid-template-columns: 1fr; }
                .hr-shc-hero h1 { font-size: 24px; }
            }
        </style>
    `;

    $(page.main).append(html);

    function getRoute(routeOverride, name) {
        if (routeOverride) return routeOverride;
        return `/app/list/${name}`;
    }

    window.openHrItem = function (routeOverride, name) {
        const url = getRoute(routeOverride, name);
        const win = window.open(url, '_blank');
        if (win) win.focus(); else window.location.href = url;
    };

    window.toggleHrFavorite = function (id) {
        let favorites = JSON.parse(localStorage.getItem('hr_shc_favorites') || '[]');
        const index = favorites.indexOf(id);
        if (index > -1) favorites.splice(index, 1); else favorites.push(id);
        localStorage.setItem('hr_shc_favorites', JSON.stringify(favorites));

        document.querySelectorAll('.fav-btn').forEach(btn => {
            const name = btn.closest('.hr-shc-item').dataset.name;
            if (favorites.includes(name)) {
                btn.textContent = '♥';
                btn.classList.add('active');
            } else {
                btn.textContent = '♡';
                btn.classList.remove('active');
            }
        });
        updateStats();
    };

    function updateStats() {
        const favorites = JSON.parse(localStorage.getItem('hr_shc_favorites') || '[]');
        document.getElementById('favorite-count').textContent = favorites.length;
    }

    function applyFilter(filter) {
        const groups = document.querySelectorAll('.hr-shc-group');
        const empty = document.getElementById('hr-shc-empty');
        let visibleCount = 0;
        const searchLower = filter.toLowerCase().trim();

        groups.forEach(group => {
            let groupHasVisible = false;
            group.querySelectorAll('.hr-shc-item').forEach(item => {
                const name = item.dataset.name.toLowerCase();
                const isVisible = !searchLower || name.includes(searchLower);
                item.style.display = isVisible ? 'flex' : 'none';
                if (isVisible) { groupHasVisible = true; visibleCount++; }
            });
            group.style.display = groupHasVisible ? 'flex' : 'none';
        });

        empty.style.display = visibleCount === 0 ? 'block' : 'none';
    }

    document.getElementById('hr-shc-search').addEventListener('input', function () {
        applyFilter(this.value);
    });

    const favorites = JSON.parse(localStorage.getItem('hr_shc_favorites') || '[]');
    document.querySelectorAll('.fav-btn').forEach(btn => {
        const name = btn.closest('.hr-shc-item').dataset.name;
        if (favorites.includes(name)) {
            btn.textContent = '♥';
            btn.classList.add('active');
        } else {
            btn.textContent = '♡';
        }
    });

    updateStats();

    window.hrShc = { GROUPS, openHrItem, toggleHrFavorite, applyFilter };
};