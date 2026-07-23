// Copyright (c) 2026, Ecclesia and contributors
// For license information, please see license.txt

frappe.ui.form.on('CRM Meeting', {
    setup: function(frm) {
        // Make the meeting date and duration more interactive
        frm.set_query('lead', function() {
            return {
                filters: {
                    status: 'Open'
                }
            };
        });
        
        frm.set_query('opportunity', function() {
            return {
                filters: {
                    status: ['in', ['Open', 'Proposal Sent']]
                }
            };
        });
        
        frm.set_query('deal', function() {
            return {
                filters: {
                    status: ['in', ['Negotiation', 'Won']]
                }
            };
        });
    },
    
    refresh: function(frm) {
        // Add a custom button to send meeting reminder
        if (frm.doc.status === "Scheduled" && frm.doc.meeting_date) {
            frm.add_custom_button(__('Send Reminder'), function() {
                frappe.call({
                    method: "frappe.core.doctype.communication.email.make",
                    args: {
                        recipients: frm.doc.lead ? 
                            frappe.db.get_value("CRM Lead", frm.doc.lead, "email") : "",
                        subject: `Reminder: ${frm.doc.meeting_title}`,
                        content: `Dear team,<br><br>This is a reminder for the meeting "<b>${frm.doc.meeting_title}</b>" scheduled on ${frappe.datetime.str_to_user(frm.doc.meeting_date)}.<br><br>Agenda: ${frm.doc.agenda || "No agenda provided."}<br><br>Thank you.`
                    },
                    callback: function(r) {
                        frappe.msgprint(__('Reminder email sent successfully.'));
                    }
                });
            }, __('Action'));
        }
        
        // Refresh the HTML dashboard
        refresh_html_dashboard(frm);
    },
    
    meeting_date: function(frm) {
        // Auto-fill meeting title if empty and lead exists
        if (!frm.doc.meeting_title && frm.doc.lead) {
            frappe.db.get_value("CRM Lead", frm.doc.lead, "lead_name", (r) => {
                if (r.lead_name) {
                    frm.set_value("meeting_title", `Meeting with ${r.lead_name}`);
                }
            });
        }
        
        // Update the dashboard when date changes
        refresh_html_dashboard(frm);
    },
    
    lead: function(frm) {
        if (frm.doc.lead && !frm.doc.meeting_title) {
            frappe.db.get_value("CRM Lead", frm.doc.lead, "lead_name", (r) => {
                if (r.lead_name) {
                    frm.set_value("meeting_title", `Meeting with ${r.lead_name}`);
                }
            });
        }
    },
    
    status: function(frm) {
        // If completed, auto-populate meeting notes reminder
        if (frm.doc.status === "Completed" && !frm.doc.meeting_notes) {
            frappe.confirm(
                __('Meeting marked as completed but no notes added. Would you like to add notes now?'),
                () => {
                    frm.set_value("meeting_notes", "Key discussion points:\n\nAction items:\n\nDecisions made:");
                    frm.refresh_field("meeting_notes");
                }
            );
        }
    }
});

// ==========================================
// STUNNING HTML DASHBOARD WITH REAL ANALYTICS
// ==========================================

function refresh_html_dashboard(frm) {
    if (!frm.get_field('html_dashboard')) return;
    
    // Fetch live analytics
    frappe.call({
        method: "ecclesia.ecclesia.doctype.crm_meeting.crm_meeting.get_meeting_analytics",
        callback: function(response) {
            if (response.message) {
                const data = response.message;
                const html = build_dashboard_html(frm, data);
                $(frm.get_field('html_dashboard').wrapper).html(html);
            } else {
                $(frm.get_field('html_dashboard').wrapper).html('<div class="alert alert-info">Loading dashboard...</div>');
            }
        }
    });
}

function build_dashboard_html(frm, analytics) {
    // Create status badges chart
    let statusHtml = '';
    if (analytics.status_breakdown && analytics.status_breakdown.length) {
        analytics.status_breakdown.forEach(item => {
            let badgeClass = 'primary';
            if (item.status === 'Completed') badgeClass = 'success';
            else if (item.status === 'Cancelled') badgeClass = 'danger';
            else if (item.status === 'No-show') badgeClass = 'warning';
            else badgeClass = 'info';
            
            statusHtml += `<div class="col-md-4 text-center mb-3">
                <span class="indicator-pill ${badgeClass}">${item.status}</span>
                <h3 class="mt-2">${item.count}</h3>
            </div>`;
        });
    }
    
    // Type breakdown list
    let typeHtml = '';
    if (analytics.type_breakdown && analytics.type_breakdown.length) {
        typeHtml = '<ul class="list-unstyled">';
        analytics.type_breakdown.forEach(item => {
            typeHtml += `<li><strong>${item.meeting_type || 'Other'}</strong>: ${item.count} meetings</li>`;
        });
        typeHtml += '</ul>';
    } else {
        typeHtml = '<p class="text-muted">No data yet</p>';
    }
    
    // Upcoming meetings
    let upcomingHtml = '';
    if (analytics.upcoming_meetings && analytics.upcoming_meetings.length) {
        upcomingHtml = '<div class="list-group">';
        analytics.upcoming_meetings.forEach(m => {
            upcomingHtml += `<div class="list-group-item">
                <strong>${m.meeting_title}</strong><br>
                <small>${frappe.datetime.str_to_user(m.meeting_date)} • ${m.meeting_type || 'Meeting'}</small>
            </div>`;
        });
        upcomingHtml += '</div>';
    } else {
        upcomingHtml = '<p class="text-muted">No upcoming meetings in the next 7 days.</p>';
    }
    
    return `
        <div style="padding: 15px;">
            <!-- KPI Row -->
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-muted">Total Meetings (30d)</h5>
                            <h2 class="card-text text-primary">${analytics.total_meetings_last_30d || 0}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-muted">Completion Rate</h5>
                            <h2 class="card-text text-success">${analytics.completion_rate || 0}%</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-muted">This Meeting Duration</h5>
                            <h2 class="card-text text-info">${frm.doc.duration_mins || 0} min</h2>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Charts Row -->
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-light">
                            <strong>📊 Meetings by Status</strong>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                ${statusHtml || '<div class="col-12 text-muted">No status data</div>'}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-light">
                            <strong>📈 Meetings by Type</strong>
                        </div>
                        <div class="card-body">
                            ${typeHtml}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Upcoming Meetings -->
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-light">
                            <strong>📅 Upcoming Meetings (next 7 days)</strong>
                        </div>
                        <div class="card-body">
                            ${upcomingHtml}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Additional Insight -->
            <div class="row mt-3">
                <div class="col-12">
                    <div class="alert alert-secondary" role="alert">
                        <i class="fa fa-lightbulb-o"></i> <strong>Insight:</strong> 
                        ${analytics.completion_rate > 70 ? 'Great completion rate! Keep engaging your leads.' : 
                          'Try following up more consistently to improve meeting completion.'}
                    </div>
                </div>
            </div>
        </div>
    `;
}