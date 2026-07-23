// Copyright (c) 2026, Value Impacts Consulting
// Copyright (c) 2026, Ecclesia and contributors
// For license information, please see license.txt

frappe.ui.form.on('CRM Quota Target', {
    setup: function(frm) {
        // Set default period based on current date
        if (frm.is_new() && !frm.doc.period) {
            set_default_period(frm);
        }
        
        // Add dynamic period start/end based on period selection
        frm.set_query('rep', function() {
            return {
                filters: {
                    'user_type': 'System User',
                    'enabled': 1
                }
            };
        });
    },
    
    refresh: function(frm) {
        // Add custom buttons
        add_quota_buttons(frm);
        
        // Refresh analytics dashboard
        refresh_quota_dashboard(frm);
        
        // Add progress indicators in the form
        add_progress_indicators(frm);
    },
    
    period: function(frm) {
        if (frm.doc.period && frm.is_new()) {
            auto_set_period_dates(frm);
        }
    },
    
    target_value: function(frm) {
        calculate_achievement(frm);
    },
    
    achieved_value: function(frm) {
        calculate_achievement(frm);
    },
    
    target_deals: function(frm) {
        calculate_achievement(frm);
    },
    
    achieved_deals: function(frm) {
        calculate_achievement(frm);
    },
    
    rep: function(frm) {
        // Fetch previous quota for this rep
        if (frm.doc.rep && frm.is_new()) {
            fetch_previous_quota(frm);
        }
    }
});

// ==========================================
// STUNNING QUOTA DASHBOARD WITH REAL-TIME ANALYTICS
// ==========================================

function refresh_quota_dashboard(frm) {
    if (!frm.get_field('html_dashboard')) return;
    
    frappe.call({
        method: "ecclesia.ecclesia.doctype.crm_quota_target.crm_quota_target.get_quota_analytics",
        args: {
            rep: frm.doc.rep,
            period: frm.doc.period
        },
        callback: function(response) {
            if (response.message) {
                const analytics = response.message;
                const html = build_quota_dashboard_html(frm, analytics);
                $(frm.get_field('html_dashboard').wrapper).html(html);
            } else {
                $(frm.get_field('html_dashboard').wrapper).html(`
                    <div class="alert alert-info text-center p-5">
                        <i class="fa fa-chart-line fa-3x mb-3"></i>
                        <h4>Enter quota details to see analytics</h4>
                        <p>Fill in the target values and save to view performance dashboard.</p>
                    </div>
                `);
            }
        }
    });
}

function build_quota_dashboard_html(frm, analytics) {
    // Handle team analytics (multiple reps)
    if (analytics.individual && analytics.team) {
        return build_team_dashboard_html(frm, analytics);
    }
    
    // Individual rep dashboard
    const quota = analytics;
    if (!quota.rep_name) return '<div class="alert alert-warning">No data available</div>';
    
    const status = quota.status;
    const valueAchieved = quota.value_achievement || 0;
    const dealsAchieved = quota.deals_achievement || 0;
    const daysRemaining = quota.days_remaining || 0;
    
    return `
        <div style="padding: 20px;">
            <!-- Header Section with Rep Info -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card bg-gradient-primary text-white" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-8">
                                    <h3>${quota.rep_name}</h3>
                                    <p class="mb-0">${quota.period} • ${formatDate(quota.period_start)} to ${formatDate(quota.period_end)}</p>
                                    <p class="mb-0"><small>${daysRemaining} days remaining</small></p>
                                </div>
                                <div class="col-md-4 text-right">
                                    <div class="status-badge" style="background: rgba(255,255,255,0.2); border-radius: 20px; padding: 5px 15px; display: inline-block;">
                                        ${status.icon} ${status.status}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- KPI Cards -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Value Achievement</h6>
                            <h2 class="card-text ${getAchievementColor(valueAchieved)}">${valueAchieved.toFixed(1)}%</h2>
                            <small>${formatCurrency(quota.achieved_value)} / ${formatCurrency(quota.target_value)}</small>
                            <div class="progress mt-2" style="height: 8px;">
                                <div class="progress-bar ${getProgressBarClass(valueAchieved)}" 
                                     style="width: ${Math.min(valueAchieved, 100)}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Deals Achievement</h6>
                            <h2 class="card-text ${getAchievementColor(dealsAchieved)}">${dealsAchieved.toFixed(1)}%</h2>
                            <small>${quota.achieved_deals || 0} / ${quota.target_deals || 0} deals</small>
                            <div class="progress mt-2" style="height: 8px;">
                                <div class="progress-bar ${getProgressBarClass(dealsAchieved)}" 
                                     style="width: ${Math.min(dealsAchieved, 100)}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Remaining Value</h6>
                            <h2 class="card-text text-warning">${formatCurrency(Math.max(quota.target_value - quota.achieved_value, 0))}</h2>
                            <small>to reach quota</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Daily Run Rate</h6>
                            <h2 class="card-text text-info">${calculateDailyRunRate(quota)}</h2>
                            <small>needed per day</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Performance Charts -->
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-light">
                            <strong>📊 Value Achievement Trend</strong>
                        </div>
                        <div class="card-body">
                            <canvas id="valueTrendChart" height="200"></canvas>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-light">
                            <strong>🎯 Activity Metrics</strong>
                        </div>
                        <div class="card-body">
                            <div class="row text-center">
                                <div class="col-6">
                                    <h4>${quota.actual_deals_data?.won_deals || 0}</h4>
                                    <small class="text-muted">Won Deals</small>
                                </div>
                                <div class="col-6">
                                    <h4>${quota.actual_deals_data?.completed_meetings || 0}</h4>
                                    <small class="text-muted">Meetings Completed</small>
                                </div>
                            </div>
                            <hr>
                            <div class="text-center">
                                <strong>Conversion Rate</strong>
                                <h3>${calculateConversionRate(quota)}%</h3>
                                <small class="text-muted">Meetings to Deals</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Recommendations -->
            <div class="row">
                <div class="col-12">
                    <div class="alert ${getRecommendationClass(valueAchieved, daysRemaining)}">
                        <i class="fa fa-lightbulb-o"></i> 
                        <strong>Recommendation:</strong> ${getRecommendation(valueAchieved, daysRemaining, quota.target_value - quota.achieved_value)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function build_team_dashboard_html(frm, analytics) {
    const team = analytics.team;
    const individuals = analytics.individual;
    
    // Build leaderboard
    let leaderboardHtml = '<div class="list-group">';
    individuals.sort((a, b) => b.value_achievement - a.value_achievement).forEach((rep, index) => {
        leaderboardHtml += `
            <div class="list-group-item">
                <div class="row">
                    <div class="col-1"><strong>#${index + 1}</strong></div>
                    <div class="col-4">${rep.rep_name}</div>
                    <div class="col-3">
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar ${getProgressBarClass(rep.value_achievement)}" 
                                 style="width: ${Math.min(rep.value_achievement, 100)}%">
                                ${rep.value_achievement.toFixed(0)}%
                            </div>
                        </div>
                    </div>
                    <div class="col-2">${formatCurrency(rep.achieved_value)}</div>
                    <div class="col-2">${rep.status.icon} ${rep.status.status}</div>
                </div>
            </div>
        `;
    });
    leaderboardHtml += '</div>';
    
    return `
        <div style="padding: 20px;">
            <!-- Team KPI Row -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center bg-primary text-white">
                        <div class="card-body">
                            <h6>Team Achievement</h6>
                            <h2>${team.team_value_achievement.toFixed(1)}%</h2>
                            <small>${formatCurrency(team.total_team_achieved)} / ${formatCurrency(team.total_team_target)}</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center bg-success text-white">
                        <div class="card-body">
                            <h6>Quota Achieved</h6>
                            <h2>${team.reps_achieved_quota} / ${team.active_reps}</h2>
                            <small>reps hit target</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center bg-warning text-white">
                        <div class="card-body">
                            <h6>At Risk</h6>
                            <h2>${team.reps_at_risk}</h2>
                            <small>reps need attention</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center bg-info text-white">
                        <div class="card-body">
                            <h6>Top Performer</h6>
                            <h6>${team.top_performer?.rep_name || 'N/A'}</h6>
                            <small>${team.top_performer?.value_achievement.toFixed(0)}% achieved</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Leaderboard -->
            <div class="card">
                <div class="card-header bg-light">
                    <strong>🏆 Team Leaderboard</strong>
                </div>
                <div class="card-body">
                    ${leaderboardHtml}
                </div>
            </div>
        </div>
    `;
}

// Helper Functions
function calculate_achievement(frm) {
    if (frm.doc.target_value && frm.doc.target_value > 0) {
        const valuePct = ((frm.doc.achieved_value || 0) / frm.doc.target_value) * 100;
        frm.set_df_property('achieved_value', 'description', `${valuePct.toFixed(1)}% of target`);
    }
    
    if (frm.doc.target_deals && frm.doc.target_deals > 0) {
        const dealsPct = ((frm.doc.achieved_deals || 0) / frm.doc.target_deals) * 100;
        frm.set_df_property('achieved_deals', 'description', `${dealsPct.toFixed(1)}% of target`);
    }
}

function add_progress_indicators(frm) {
    // Add visual progress rings in the form
    if (frm.doc.target_value && frm.doc.achieved_value) {
        const pct = (frm.doc.achieved_value / frm.doc.target_value) * 100;
        frm.get_field('target_value').$wrapper.find('.control-value').append(`
            <div class="progress mt-1" style="height: 3px; width: 100px; display: inline-block; margin-left: 10px;">
                <div class="progress-bar bg-success" style="width: ${Math.min(pct, 100)}%"></div>
            </div>
        `);
    }
}

function add_quota_buttons(frm) {
    frm.add_custom_button(__('View Team Dashboard'), function() {
        refresh_quota_dashboard(frm);
    }, __('Analytics'));
    
    frm.add_custom_button(__('Compare Periods'), function() {
        show_period_comparison(frm);
    }, __('Analytics'));
}

function set_default_period(frm) {
    const now = new Date();
    const quarter = Math.floor(now.getMonth() / 3) + 1;
    frm.set_value('period', `Q${quarter}`);
    auto_set_period_dates(frm);
}

function auto_set_period_dates(frm) {
    const period = frm.doc.period;
    let start_date, end_date;
    const now = new Date();
    const year = now.getFullYear();
    
    if (period === 'Q1') {
        start_date = `${year}-01-01`;
        end_date = `${year}-03-31`;
    } else if (period === 'Q2') {
        start_date = `${year}-04-01`;
        end_date = `${year}-06-30`;
    } else if (period === 'Q3') {
        start_date = `${year}-07-01`;
        end_date = `${year}-09-30`;
    } else if (period === 'Q4') {
        start_date = `${year}-10-01`;
        end_date = `${year}-12-31`;
    } else if (period === 'H1') {
        start_date = `${year}-01-01`;
        end_date = `${year}-06-30`;
    } else if (period === 'H2') {
        start_date = `${year}-07-01`;
        end_date = `${year}-12-31`;
    } else if (period === 'Annual') {
        start_date = `${year}-01-01`;
        end_date = `${year}-12-31`;
    }
    
    if (start_date && end_date) {
        frm.set_value('period_start', start_date);
        frm.set_value('period_end', end_date);
    }
}

function fetch_previous_quota(frm) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "CRM Quota Target",
            filters: { rep: frm.doc.rep },
            fields: ["target_value", "achieved_value", "period"],
            limit: 1,
            order_by: "creation desc"
        },
        callback: function(r) {
            if (r.message && r.message.length) {
                const prev = r.message[0];
                frm.set_df_property('target_value', 'description', `Previous: ${formatCurrency(prev.target_value)} (${prev.period})`);
            }
        }
    });
}

function calculateDailyRunRate(quota) {
    const remaining = Math.max(quota.target_value - quota.achieved_value, 0);
    const daysLeft = quota.days_remaining || 1;
    const daily = remaining / daysLeft;
    return formatCurrency(daily);
}

function calculateConversionRate(quota) {
    const meetings = quota.actual_deals_data?.completed_meetings || 0;
    const deals = quota.actual_deals_data?.won_deals || 0;
    if (meetings === 0) return 0;
    return ((deals / meetings) * 100).toFixed(1);
}

function getAchievementColor(pct) {
    if (pct >= 100) return 'text-success';
    if (pct >= 75) return 'text-primary';
    if (pct >= 50) return 'text-warning';
    return 'text-danger';
}

function getProgressBarClass(pct) {
    if (pct >= 100) return 'bg-success';
    if (pct >= 75) return 'bg-primary';
    if (pct >= 50) return 'bg-warning';
    return 'bg-danger';
}

function getRecommendationClass(achieved, daysLeft) {
    if (achieved >= 100) return 'alert-success';
    if (achieved >= 75 && daysLeft < 7) return 'alert-warning';
    if (achieved < 50 && daysLeft < 14) return 'alert-danger';
    return 'alert-info';
}

function getRecommendation(achieved, daysLeft, remainingAmount) {
    if (achieved >= 100) {
        return "Excellent work! You've exceeded your quota. Consider setting stretch goals for extra commission.";
    }
    if (achieved >= 75) {
        if (daysLeft < 7) {
            return `Close the gap! Only ${formatCurrency(remainingAmount)} remaining with ${daysLeft} days left. Focus on high-value deals.`;
        }
        return "You're on track! Maintain momentum to hit your quota comfortably.";
    }
    if (achieved >= 50) {
        if (daysLeft < 14) {
            return `Critical period! Need ${formatCurrency(remainingAmount)} in ${daysLeft} days. Prioritize urgent deals and follow-ups.`;
        }
        return "Behind target but time remains. Increase daily activities and focus on conversion.";
    }
    return "Quota at risk. Immediate action needed: Reach out to warm leads, increase meeting volume, and focus on quick-win opportunities.";
}

function formatCurrency(amount) {
    if (!amount) return '₦0';
    return '₦' + amount.toLocaleString('en-NG', {
        maximumFractionDigits: 0
    });
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-NG');
}