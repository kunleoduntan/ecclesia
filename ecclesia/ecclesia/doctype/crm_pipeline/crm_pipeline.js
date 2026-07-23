// Copyright (c) 2026, Value Impacts Consulting
// Copyright (c) 2026, Ecclesia and contributors
// For license information, please see license.txt

frappe.ui.form.on('CRM Pipeline', {
    setup: function(frm) {
        // Add custom validation for pipeline name
        frm.set_df_property('pipeline_name', 'reqd', 1);
        
        // Set company filter based on user permissions
        if (frappe.boot.user.has_default_company) {
            frm.set_value('company', frappe.defaults.get_default('company'));
        }
    },
    
    refresh: function(frm) {
        // Add custom buttons
        add_pipeline_buttons(frm);
        
        // Show pipeline analytics dashboard
        refresh_pipeline_dashboard(frm);
        
        // Add stage management section if not already there
        add_stage_management_section(frm);
    },
    
    pipeline_name: function(frm) {
        // Auto-generate description if empty
        if (!frm.doc.description && frm.doc.pipeline_name) {
            frm.set_value('description', `Sales pipeline for ${frm.doc.pipeline_name}`);
        }
    },
    
    is_default: function(frm) {
        if (frm.doc.is_default) {
            frappe.show_alert({
                message: __('This pipeline is now the default.'),
                indicator: 'green'
            }, 3);
        }
    },
    
    company: function(frm) {
        // Refresh dashboard when company changes
        refresh_pipeline_dashboard(frm);
    }
});

// ==========================================
// STUNNING PIPELINE ANALYTICS DASHBOARD
// ==========================================

function refresh_pipeline_dashboard(frm) {
    // Check if we have an HTML field - if not, we'll add it dynamically
    if (!frm.fields_dict.pipeline_analytics) {
        // Add analytics tab with HTML field dynamically
        add_analytics_tab(frm);
        return;
    }
    
    // Fetch pipeline analytics
    frappe.call({
        method: "ecclesia.ecclesia.doctype.crm_pipeline.crm_pipeline.get_pipeline_analytics",
        args: {
            pipeline_name: frm.doc.name
        },
        callback: function(response) {
            if (response.message && response.message.pipeline_name) {
                const analytics = response.message;
                const html = build_pipeline_dashboard_html(frm, analytics);
                $(frm.fields_dict.pipeline_analytics.wrapper).html(html);
            } else {
                $(frm.fields_dict.pipeline_analytics.wrapper).html(`
                    <div class="alert alert-info text-center p-5">
                        <i class="fa fa-bar-chart fa-3x mb-3"></i>
                        <h4>No analytics data available</h4>
                        <p>Create stages and add deals to see pipeline analytics.</p>
                    </div>
                `);
            }
        }
    });
}

function add_analytics_tab(frm) {
    // Add analytics tab if it doesn't exist
    const analytics_tab = {
        fieldname: "analytics_tab",
        fieldtype: "Tab Break",
        label: "📊 Pipeline Analytics",
        insert_after: "description"
    };
    
    const html_field = {
        fieldname: "pipeline_analytics",
        fieldtype: "HTML",
        label: "Analytics Dashboard",
        fieldtype: "HTML"
    };
    
    if (!frm.fields_dict.analytics_tab) {
        frm.add_custom_field(analytics_tab);
        frm.add_custom_field(html_field);
        frm.refresh_fields();
    }
    
    // Refresh after adding fields
    setTimeout(() => refresh_pipeline_dashboard(frm), 500);
}

function add_stage_management_section(frm) {
    // Add a quick link to manage stages
    frm.add_custom_button(__('Manage Stages'), function() {
        frappe.set_route('List', 'CRM Stage', {'pipeline': frm.doc.name});
    }, __('Pipeline'));
    
    frm.add_custom_button(__('View Pipeline Board'), function() {
        frappe.set_route('query-report', 'Pipeline Analysis', {'pipeline': frm.doc.name});
    }, __('Analytics'));
}

function add_pipeline_buttons(frm) {
    // Clone button
    frm.add_custom_button(__('Clone Pipeline'), function() {
        frappe.prompt([
            {'fieldname': 'new_name', 'fieldtype': 'Data', 'label': 'New Pipeline Name', 'reqd': 1},
            {'fieldname': 'copy_stages', 'fieldtype': 'Check', 'label': 'Copy Stages', 'default': 1}
        ], function(values) {
            frappe.call({
                method: "frappe.client.copy_doc",
                args: {
                    doctype: "CRM Pipeline",
                    name: frm.doc.name,
                    data: {
                        pipeline_name: values.new_name,
                        is_default: 0,
                        description: `Clone of ${frm.doc.pipeline_name}`
                    }
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(__('Pipeline cloned successfully!'));
                        frappe.set_route('Form', 'CRM Pipeline', r.message.name);
                    }
                }
            });
        }, __('Clone Pipeline'), __('Create'));
    }, __('Actions'));
}

function build_pipeline_dashboard_html(frm, analytics) {
    // Build stage progress bars
    let stageHtml = '';
    if (analytics.stage_breakdown && analytics.stage_breakdown.length) {
        stageHtml = '<div class="pipeline-stages">';
        
        analytics.stage_breakdown.forEach((stage, index) => {
            const width = (stage.deal_count / Math.max(analytics.total_deals, 1)) * 100;
            const valueWidth = (stage.total_value / Math.max(analytics.total_pipeline_value, 1)) * 100;
            
            stageHtml += `
                <div class="stage-card mb-3" style="border-left: 4px solid ${getStageColor(stage.probability)};">
                    <div class="stage-header clearfix">
                        <strong class="pull-left">${stage.stage_name}</strong>
                        <span class="pull-right text-muted">${stage.probability}% probability</span>
                    </div>
                    <div class="stage-stats row mt-2">
                        <div class="col-6">
                            <small class="text-muted">Deals</small>
                            <h5 class="mb-0">${stage.deal_count}</h5>
                            <div class="progress mt-1" style="height: 4px;">
                                <div class="progress-bar bg-info" style="width: ${width}%"></div>
                            </div>
                        </div>
                        <div class="col-6">
                            <small class="text-muted">Value</small>
                            <h5 class="mb-0">${formatCurrency(stage.total_value)}</h5>
                            <div class="progress mt-1" style="height: 4px;">
                                <div class="progress-bar bg-success" style="width: ${valueWidth}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        stageHtml += '</div>';
    } else {
        stageHtml = '<p class="text-muted text-center">No stages defined for this pipeline.</p>';
    }
    
    return `
        <div style="padding: 20px;">
            <!-- Header Stats -->
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card bg-gradient-primary text-white">
                        <div class="card-body">
                            <h6 class="card-title">Total Pipeline Value</h6>
                            <h2 class="card-text">${formatCurrency(analytics.total_pipeline_value || 0)}</h2>
                            <small>Across ${analytics.total_deals || 0} deals</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-gradient-success text-white">
                        <div class="card-body">
                            <h6 class="card-title">Weighted Pipeline</h6>
                            <h2 class="card-text">${formatCurrency(analytics.weighted_pipeline_value || 0)}</h2>
                            <small>Probability-adjusted value</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-gradient-info text-white">
                        <div class="card-body">
                            <h6 class="card-title">Completion Rate</h6>
                            <h2 class="card-text">${analytics.completion_rate ? analytics.completion_rate.toFixed(1) : 0}%</h2>
                            <small>Deals reaching final stage</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Pipeline Funnel Visualization -->
            <div class="card mb-4">
                <div class="card-header bg-light">
                    <strong>📈 Pipeline Funnel - ${analytics.pipeline_name}</strong>
                    ${analytics.is_default ? '<span class="badge badge-success ml-2">Default</span>' : ''}
                    ${analytics.company ? `<span class="badge badge-info ml-2">${analytics.company}</span>` : ''}
                </div>
                <div class="card-body">
                    ${stageHtml}
                </div>
            </div>
            
            <!-- Quick Actions -->
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-light">
                            <strong>🚀 Quick Actions</strong>
                        </div>
                        <div class="card-body">
                            <button class="btn btn-primary btn-sm mr-2" onclick="frappe.set_route('List', 'CRM Stage', {'pipeline': '${frm.doc.name}')">
                                <i class="fa fa-tasks"></i> Manage Stages
                            </button>
                            <button class="btn btn-success btn-sm mr-2" onclick="frappe.set_route('List', 'CRM Deal', {'pipeline': '${frm.doc.name}')">
                                <i class="fa fa-briefcase"></i> View Deals
                            </button>
                            <button class="btn btn-info btn-sm" onclick="createNewStage('${frm.doc.name}')">
                                <i class="fa fa-plus"></i> Add Stage
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-light">
                            <strong>💡 Pipeline Insights</strong>
                        </div>
                        <div class="card-body">
                            <small class="text-muted">
                                ${getPipelineInsight(analytics)}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Helper Functions
function getStageColor(probability) {
    if (probability >= 75) return '#28a745';
    if (probability >= 50) return '#ffc107';
    if (probability >= 25) return '#fd7e14';
    return '#dc3545';
}

function formatCurrency(amount) {
    if (!amount) return '₹0';
    return '₹' + amount.toLocaleString('en-IN', {
        maximumFractionDigits: 0
    });
}

function getPipelineInsight(analytics) {
    if (!analytics.total_deals || analytics.total_deals === 0) {
        return "No deals in pipeline yet. Start adding deals to track your sales progress.";
    }
    
    if (analytics.completion_rate < 30) {
        return "⚠️ Low completion rate. Focus on moving deals through later stages and improving closing techniques.";
    } else if (analytics.completion_rate < 70) {
        return "📊 Moderate completion rate. Identify bottlenecks in middle stages to improve flow.";
    } else {
        return "🎯 Excellent completion rate! Your pipeline is healthy and converting well.";
    }
}

// Global function for stage creation
window.createNewStage = function(pipeline_name) {
    frappe.new_doc('CRM Stage', {
        pipeline: pipeline_name
    });
};