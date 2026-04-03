
frappe.ui.form.on('Annual Budget', {
    onload: function(frm) {
        if (frm.fields_dict.user_manual_html) {
            setTimeout(() => {
                render_user_manual(frm);
            }, 1000);
        }
    },
    
    refresh: function(frm) {
        if (frm.fields_dict.user_manual_html && !frm.user_manual_loaded) {
            render_user_manual(frm);
            frm.user_manual_loaded = true;
        }
    }
});

function render_user_manual(frm) {
    frm.set_df_property('user_manual_html', 'options', '<div style="padding: 20px; text-align: center;"><i class="fa fa-spinner fa-spin"></i> Loading manual...</div>');
    
    let manual_html = get_complete_manual_html();
    
    frm.set_df_property('user_manual_html', 'options', manual_html);
    frm.fields_dict.user_manual_html.df.options = manual_html;
    frm.refresh_field('user_manual_html');
    
    setTimeout(() => {
        setup_manual_interactivity(frm);
    }, 100);
}

function setup_manual_interactivity(frm) {
    let $wrapper = frm.fields_dict.user_manual_html.$wrapper;
    
    if (!$wrapper || !$wrapper.length) return;
    
    $wrapper.find('.tab-content').hide();
    $wrapper.find('.tab-content.active').show();
    
    $wrapper.find('.tab').off('click').on('click', function(e) {
        e.preventDefault();
        $wrapper.find('.tab').removeClass('active');
        $(this).addClass('active');
        $wrapper.find('.tab-content').removeClass('active').hide();
        let tabName = $(this).attr('data-tab');
        $wrapper.find('#' + tabName).addClass('active').show();
        $wrapper.find('.manual-content').scrollTop(0);
    });
    
    $wrapper.find('#searchInput').off('keyup').on('keyup', function() {
        let searchTerm = $(this).val().toLowerCase();
        
        if (searchTerm === '') {
            $wrapper.find('.section').show();
            $wrapper.find('.search-highlight').each(function() {
                $(this).replaceWith($(this).text());
            });
            return;
        }
        
        let activeTab = $wrapper.find('.tab-content.active');
        activeTab.find('.section').each(function() {
            let $section = $(this);
            let sectionText = $section.text().toLowerCase();
            
            if (sectionText.includes(searchTerm)) {
                $section.show();
                highlightText($section, searchTerm);
            } else {
                $section.hide();
            }
        });
    });
    
    $wrapper.find('.accordion-header').off('click').on('click', function() {
        let $header = $(this);
        let $content = $header.next('.accordion-content');
        let $icon = $header.find('.accordion-icon');
        
        $content.toggleClass('active');
        $header.toggleClass('active');
        
        if ($content.hasClass('active')) {
            $content.css('max-height', $content.prop('scrollHeight') + 'px');
            $icon.css('transform', 'rotate(180deg)');
        } else {
            $content.css('max-height', '0');
            $icon.css('transform', 'rotate(0deg)');
        }
    });
}

function highlightText($element, searchTerm) {
    $element.find('.search-highlight').each(function() {
        $(this).replaceWith($(this).text());
    });
    
    let regex = new RegExp('(' + searchTerm + ')', 'gi');
    
    walkTextNodes($element, function(node) {
        let text = node.nodeValue;
        if (regex.test(text)) {
            let span = document.createElement('span');
            span.innerHTML = text.replace(regex, '<span class="search-highlight">$1</span>');
            node.parentNode.replaceChild(span, node);
        }
    });
}

function walkTextNodes($element, callback) {
    $element.contents().each(function() {
        if (this.nodeType === 3) {
            callback(this);
        } else if (this.nodeType === 1 && this.nodeName !== 'SCRIPT') {
            walkTextNodes($(this), callback);
        }
    });
}

function get_complete_manual_html() {
    return `
    <div class="manual-container">
        <div class="manual-header">
            <h1><span>📊</span> Annual Budget System - Complete User Manual</h1>
            <p>Master comprehensive budgeting with AI projections, scenario planning, branch/cost center allocations, variance tracking, and intelligent automation.</p>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 Search the manual... (try 'allocation', 'scenario', 'variance', 'AI projection')">
        </div>
        
        <div class="tabs-container">
            <div class="tabs">
                <button class="tab active" data-tab="overview">📋 Overview</button>
                <button class="tab" data-tab="getting-started">🚀 Getting Started</button>
                <button class="tab" data-tab="allocations">🏢 Allocations</button>
                <button class="tab" data-tab="scenarios">🎯 Scenarios</button>
                <button class="tab" data-tab="projections">📈 Projections</button>
                <button class="tab" data-tab="variance">📊 Variance</button>
                <button class="tab" data-tab="workflows">⚙️ Workflows</button>
                <button class="tab" data-tab="advanced">🔧 Advanced</button>
                <button class="tab" data-tab="faq">❓ FAQ</button>
            </div>
            
            <div class="manual-content">
                <!-- OVERVIEW TAB -->
                <div id="overview" class="tab-content active">
                    <div class="section">
                        <h2>🎯 System Overview</h2>
                        <p>The Annual Budget system is a world-class financial planning platform combining traditional budgeting with AI-powered projections, scenario analysis, and intelligent variance tracking. It transforms budgeting from a static exercise into a dynamic strategic planning tool.</p>
                        
                        <div class="feature-grid">
                            <div class="feature-card">
                                <div class="feature-icon">🏢</div>
                                <h4>Group Budgeting</h4>
                                <p>Create master budgets and intelligently distribute them across branches and cost centers using multiple allocation methods.</p>
                            </div>
                            
                            <div class="feature-card">
                                <div class="feature-icon">🎭</div>
                                <h4>Scenario Planning</h4>
                                <p>Model best case, worst case, and custom scenarios to prepare for different business conditions and market changes.</p>
                            </div>
                            
                            <div class="feature-card">
                                <div class="feature-icon">🤖</div>
                                <h4>AI Projections</h4>
                                <p>Leverage machine learning models (ARIMA, Neural Networks, Random Forest) for accurate budget forecasts.</p>
                            </div>
                            
                            <div class="feature-card">
                                <div class="feature-icon">📊</div>
                                <h4>Real-time Variance</h4>
                                <p>Monitor budget vs actual with automated alerts, variance analysis, and actionable insights.</p>
                            </div>
                            
                            <div class="feature-card">
                                <div class="feature-icon">🔄</div>
                                <h4>Multi-level Approval</h4>
                                <p>Configure approval workflows with revision tracking, digital audit trails, and automated notifications.</p>
                            </div>
                            
                            <div class="feature-card">
                                <div class="feature-icon">📈</div>
                                <h4>Rich Reporting</h4>
                                <p>Export to Excel, PDF, PowerPoint with automatic charts, conditional formatting, and executive summaries.</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>🔑 Key Concepts</h2>
                        
                        <div class="accordion">
                            <div class="accordion-item">
                                <div class="accordion-header">
                                    <span>What is a Group Budget?</span>
                                    <span class="accordion-icon">▼</span>
                                </div>
                                <div class="accordion-content">
                                    <p><strong>Group Budget</strong> is a master budget that splits into child budgets. It's ideal for corporate-level budgets needing distribution across branches, departments, or cost centers.</p>
                                    <p><strong>Example:</strong> A $10M corporate budget distributed across 5 branches based on revenue share, headcount, or custom allocation rules.</p>
                                    <p><strong>Key Features:</strong></p>
                                    <ul>
                                        <li>Automatic child budget creation</li>
                                        <li>Multiple distribution methods (Equal, Revenue-based, Headcount, etc.)</li>
                                        <li>Rollup capabilities for consolidated reporting</li>
                                        <li>Lock/unlock child budgets independently</li>
                                    </ul>
                                </div>
                            </div>
                            
                            <div class="accordion-item">
                                <div class="accordion-header">
                                    <span>Budget Scenarios Explained</span>
                                    <span class="accordion-icon">▼</span>
                                </div>
                                <div class="accordion-content">
                                    <p><strong>Scenarios</strong> let you model different potential outcomes instead of relying on a single budget figure.</p>
                                    <p><strong>Common Scenario Types:</strong></p>
                                    <ul>
                                        <li><strong>Best Case:</strong> Optimistic projections (e.g., +20% revenue growth)</li>
                                        <li><strong>Worst Case:</strong> Conservative planning (e.g., -15% revenue decline)</li>
                                        <li><strong>Most Likely:</strong> Realistic baseline expectations</li>
                                        <li><strong>Custom:</strong> Specific event-based scenarios (merger, new product launch, etc.)</li>
                                    </ul>
                                    <p><strong>Use Cases:</strong> Risk assessment, contingency planning, stress testing, board presentations.</p>
                                </div>
                            </div>
                            
                            <div class="accordion-item">
                                <div class="accordion-header">
                                    <span>AI/ML Projection Methods</span>
                                    <span class="accordion-icon">▼</span>
                                </div>
                                <div class="accordion-content">
                                    <p>The system supports multiple AI/ML models for budget forecasting:</p>
                                    <ul>
                                        <li><strong>Time Series (ARIMA):</strong> Best for seasonal patterns and trend analysis</li>
                                        <li><strong>Regression Analysis:</strong> Ideal for understanding relationships between variables</li>
                                        <li><strong>Neural Networks:</strong> Handles complex non-linear patterns</li>
                                        <li><strong>Random Forest:</strong> Robust against outliers, works with missing data</li>
                                        <li><strong>Gradient Boosting:</strong> High accuracy for structured financial data</li>
                                    </ul>
                                    <p><strong>Data Requirements:</strong> Minimum 1 year historical data; 3-5 years recommended for better accuracy.</p>
                                </div>
                            </div>
                            
                            <div class="accordion-item">
                                <div class="accordion-header">
                                    <span>Variance Analysis & Alerts</span>
                                    <span class="accordion-icon">▼</span>
                                </div>
                                <div class="accordion-content">
                                    <p><strong>Variance tracking</strong> monitors the difference between budgeted and actual amounts in real-time.</p>
                                    <p><strong>Alert Levels:</strong></p>
                                    <ul>
                                        <li><strong>Low (10-15%):</strong> Informational notifications</li>
                                        <li><strong>Medium (15-25%):</strong> Warning to budget owners</li>
                                        <li><strong>High (25-35%):</strong> Escalation to managers</li>
                                        <li><strong>Critical (>35%):</strong> Immediate action required, notify executives</li>
                                    </ul>
                                    <p><strong>Automated Actions:</strong> Email alerts, dashboard updates, variance reports, trend analysis.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📚 Budget Lifecycle</h2>
                        <div class="timeline">
                            <div class="timeline-item">
                                <div class="timeline-marker">1</div>
                                <div class="timeline-content">
                                    <h4>Draft</h4>
                                    <p>Initial budget creation, editable by creator</p>
                                </div>
                            </div>
                            <div class="timeline-item">
                                <div class="timeline-marker">2</div>
                                <div class="timeline-content">
                                    <h4>Pending Approval</h4>
                                    <p>Submitted for review, enters approval workflow</p>
                                </div>
                            </div>
                            <div class="timeline-item">
                                <div class="timeline-marker">3</div>
                                <div class="timeline-content">
                                    <h4>Approved</h4>
                                    <p>Reviewed and approved by authorized personnel</p>
                                </div>
                            </div>
                            <div class="timeline-item">
                                <div class="timeline-marker">4</div>
                                <div class="timeline-content">
                                    <h4>Active</h4>
                                    <p>In-use budget, variance tracking enabled</p>
                                </div>
                            </div>
                            <div class="timeline-item">
                                <div class="timeline-marker">5</div>
                                <div class="timeline-content">
                                    <h4>Locked/Closed</h4>
                                    <p>Finalized, no further modifications (archived)</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- GETTING STARTED TAB -->
                <div id="getting-started" class="tab-content">
                    <div class="section">
                        <h2>🚀 Quick Start Guide</h2>
                        <p>Follow these steps to create your first comprehensive budget with all features enabled.</p>
                        
                        <div class="step-card">
                            <h3><span class="step-number">1</span> Create New Budget Document</h3>
                            <p>Navigate to <span class="highlight">General Biz Apps > Annual Budget</span> and click <strong>New</strong>.</p>
                            <div class="tip-box">
                                <strong>💡 Tip:</strong> Use keyboard shortcut <kbd>Ctrl + K</kbd> then type "Annual Budget" for quick access.
                            </div>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">2</span> Fill Basic Information</h3>
                            <ul>
                                <li><strong>Company:</strong> Select your company (required)</li>
                                <li><strong>Fiscal Year:</strong> Choose relevant fiscal year (e.g., 2024-2025)</li>
                                <li><strong>Budget Name:</strong> Descriptive name (e.g., "2025 Marketing Budget - Q1-Q4")</li>
                                <li><strong>Cost Center:</strong> Primary cost center for tracking</li>
                                <li><strong>Budget Type:</strong> Operating, Capital, Revenue, or Custom</li>
                            </ul>
                            <div class="warning-box">
                                <strong>⚠️ Important:</strong> Company and Fiscal Year cannot be changed after budget approval.
                            </div>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">3</span> Configure Budget Settings</h3>
                            <p><strong>Group Budget Options:</strong></p>
                            <ul>
                                <li>Check <strong>"Is Group Budget"</strong> if this will be split into child budgets</li>
                                <li>Enable <strong>"Allow Branch Split"</strong> for branch-wise distribution</li>
                                <li>Enable <strong>"Allow Cost Center Split"</strong> for department-wise allocation</li>
                                <li>Choose distribution method (Equal, Revenue-based, Headcount, etc.)</li>
                            </ul>
                            
                            <p><strong>Projection Settings:</strong></p>
                            <ul>
                                <li>Enable <strong>"Enable Projections"</strong> for AI-powered forecasting</li>
                                <li>Select projection method (Historical Average, Linear Trend, ML-Based)</li>
                                <li>Set historical years to analyze (1-5 years)</li>
                                <li>Configure growth rate and inflation adjustments</li>
                            </ul>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">4</span> Add Budget Line Items</h3>
                            <p>In the <strong>Monthly Budget</strong> table, add your GL accounts and amounts:</p>
                            <ul>
                                <li><strong>GL Account:</strong> Select from chart of accounts</li>
                                <li><strong>Monthly Amounts:</strong> Enter budget for each month (Jan-Dec)</li>
                                <li><strong>Notes:</strong> Add explanations for specific line items</li>
                            </ul>
                            <div class="tip-box">
                                <strong>💡 Pro Tip:</strong> Use bulk edit (select multiple rows + right-click) to apply same value across months.
                            </div>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">5</span> Set Up Scenario Analysis (Optional)</h3>
                            <p>Create multiple scenarios in the <strong>Budget Scenarios</strong> tab:</p>
                            <ul>
                                <li>Click "Auto Generate Scenarios" button for automatic best/worst cases</li>
                                <li>Or manually create custom scenarios with specific adjustments</li>
                                <li>Set probability percentages for each scenario</li>
                                <li>Document key assumptions and trigger events</li>
                            </ul>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">6</span> Configure Branch/Cost Center Allocations</h3>
                            <p>If this is a group budget, distribute amounts:</p>
                            <ul>
                                <li>Go to <strong>Branch Allocations</strong> or <strong>Cost Center Allocations</strong> tab</li>
                                <li>Click "Distribute Budget" button</li>
                                <li>Review and adjust allocation percentages</li>
                                <li>System auto-calculates allocated amounts</li>
                                <li>Add allocation rationale and notes</li>
                            </ul>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">7</span> Enable Variance Tracking</h3>
                            <p>Configure automatic variance monitoring:</p>
                            <ul>
                                <li>Enable <strong>"Auto Calculate Variance"</strong></li>
                                <li>Set variance threshold percentage (e.g., 10%)</li>
                                <li>Add alert recipients (comma-separated emails)</li>
                                <li>Choose alert frequency (Daily, Weekly, Monthly)</li>
                            </ul>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">8</span> Save and Submit for Approval</h3>
                            <p>Final steps before approval:</p>
                            <ul>
                                <li>Click <strong>Save</strong> to preserve your work</li>
                                <li>Review all sections for completeness</li>
                                <li>Click <strong>Submit</strong> to send for approval</li>
                                <li>Budget enters the configured approval workflow</li>
                                <li>Approvers receive email notifications</li>
                            </ul>
                            <div class="success-box">
                                <strong>✅ Success:</strong> Your budget is now in the approval queue and can be tracked in the Budget Dashboard.
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>🎬 Common Workflows</h2>
                        
                        <div class="workflow-card">
                            <h4>📊 Simple Department Budget</h4>
                            <ol>
                                <li>Create budget for single cost center</li>
                                <li>Add GL accounts with monthly amounts</li>
                                <li>Submit for manager approval</li>
                                <li>Once approved, track variance monthly</li>
                            </ol>
                        </div>
                        
                        <div class="workflow-card">
                            <h4>🏢 Corporate Budget with Branch Split</h4>
                            <ol>
                                <li>Create group budget at corporate level</li>
                                <li>Enable branch distribution</li>
                                <li>Configure allocation rules (revenue-based)</li>
                                <li>Auto-generate child budgets for each branch</li>
                                <li>Submit parent budget for CFO approval</li>
                                <li>Branch managers review and confirm allocations</li>
                            </ol>
                        </div>
                        
                        <div class="workflow-card">
                            <h4>🎯 Strategic Budget with Scenarios</h4>
                            <ol>
                                <li>Create base budget with historical projections</li>
                                <li>Generate best/worst case scenarios</li>
                                <li>Add custom scenarios for specific events</li>
                                <li>Present all scenarios to board</li>
                                <li>Select approved scenario as active budget</li>
                                <li>Track actual vs all scenarios</li>
                            </ol>
                        </div>
                    </div>
                </div>
                
                <!-- ALLOCATIONS TAB -->
                <div id="allocations" class="tab-content">
                    <div class="section">
                        <h2>🏢 Branch & Cost Center Allocations</h2>
                        <p>Master the art of distributing budgets across organizational units with intelligent allocation methods.</p>
                    </div>
                    
                    <div class="section">
                        <h2>📍 Distribution Methods Explained</h2>
                        
                        <div class="method-card">
                            <h4>1️⃣ Equal Distribution</h4>
                            <p><strong>When to use:</strong> All branches/cost centers should receive the same amount regardless of size or performance.</p>
                            <p><strong>Formula:</strong> Total Budget ÷ Number of Units</p>
                            <p><strong>Example:</strong> $1M budget ÷ 5 branches = $200K each</p>
                            <p><strong>Best for:</strong> Standardized programs, fixed costs, uniform initiatives</p>
                        </div>
                        
                        <div class="method-card">
                            <h4>2️⃣ Proportional by Revenue</h4>
                            <p><strong>When to use:</strong> Allocate based on revenue contribution of each unit.</p>
                            <p><strong>Formula:</strong> (Unit Revenue ÷ Total Revenue) × Total Budget</p>
                            <p><strong>Example:</strong> Branch A generates 40% of revenue → gets 40% of budget</p>
                            <p><strong>Best for:</strong> Sales budgets, marketing spend, commission structures</p>
                            <p><strong>Data Required:</strong> Revenue share field populated for each branch</p>
                        </div>
                        
                        <div class="method-card">
                            <h4>3️⃣ Proportional by Headcount</h4>
                            <p><strong>When to use:</strong> Distribute based on number of employees.</p>
                            <p><strong>Formula:</strong> (Unit Headcount ÷ Total Headcount) × Total Budget</p>
                            <p><strong>Example:</strong> Branch with 50 employees out of 200 total → gets 25% of budget</p>
                            <p><strong>Best for:</strong> HR budgets, training costs, employee benefits, facility expenses</p>
                            <p><strong>Data Required:</strong> Headcount field populated for each unit</p>
                        </div>
                        
                        <div class="method-card">
                            <h4>4️⃣ Historical Spend-Based</h4>
                            <p><strong>When to use:</strong> Allocate based on past actual spending patterns.</p>
                            <p><strong>Formula:</strong> (Unit Historical Spend ÷ Total Historical Spend) × Total Budget</p>
                            <p><strong>Example:</strong> If branch spent 30% of total last year → gets 30% this year</p>
                            <p><strong>Best for:</strong> Incremental budgeting, maintaining consistency, operational costs</p>
                            <p><strong>Data Required:</strong> Historical spend field with previous year actuals</p>
                        </div>
                        
                        <div class="method-card">
                            <h4>5️⃣ Activity-Based Costing (ABC)</h4>
                            <p><strong>When to use:</strong> Allocate based on volume of activities performed.</p>
                            <p><strong>Formula:</strong> (Unit Activity Volume ÷ Total Activity Volume) × Total Budget</p>
                            <p><strong>Example:</strong> Branch processing 40% of transactions → gets 40% of processing budget</p>
                            <p><strong>Best for:</strong> Operations budgets, transaction costs, process-driven expenses</p>
                            <p><strong>Data Required:</strong> Activity volume metrics (transactions, orders, units produced)</p>
                        </div>
                        
                        <div class="method-card">
                            <h4>6️⃣ Custom Allocation</h4>
                            <p><strong>When to use:</strong> Unique business requirements need custom weighting.</p>
                            <p><strong>Formula:</strong> (Custom Weight × Base Amount) adjusted to total</p>
                            <p><strong>Example:</strong> Strategic priority branches get 1.5x weight multiplier</p>
                            <p><strong>Best for:</strong> Strategic initiatives, growth investments, special projects</p>
                            <p><strong>Setup:</strong> Define custom weight factors for each unit (default 1.0)</p>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>🔧 Step-by-Step Allocation Process</h2>
                        
                        <div class="step-card">
                            <h3><span class="step-number">1</span> Enable Group Budget</h3>
                            <ul>
                                <li>Check "Is Group Budget" in budget header</li>
                                <li>Enable "Allow Branch Split" or "Allow Cost Center Split"</li>
                                <li>Select distribution method from dropdown</li>
                            </ul>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">2</span> Prepare Allocation Data</h3>
                            <ul>
                                <li>Ensure all branches/cost centers have required data fields populated</li>
                                <li>For revenue-based: Update revenue share amounts</li>
                                <li>For headcount: Verify employee counts are current</li>
                                <li>For historical: Import previous year actuals</li>
                            </ul>
                            <div class="warning-box">
                                <strong>⚠️ Data Quality:</strong> Allocation accuracy depends on data quality. Missing data = incorrect allocations.
                            </div>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">3</span> Run Distribution</h3>
                            <ul>
                                <li>Go to "Branch Allocations" or "Cost Center Allocations" tab</li>
                                <li>Click <strong>"Distribute Budget"</strong> button</li>
                                <li>System calculates allocation percentages automatically</li>
                                <li>Review proposed allocations in the table</li>
                            </ul>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">4</span> Review and Adjust</h3>
                            <ul>
                                <li>Check that allocation percentages sum to 100%</li>
                                <li>Review allocated amounts for reasonableness</li>
                                <li>Make manual adjustments if needed (check "Manual Override")</li>
                                <li>Add allocation rationale notes for documentation</li>
                            </ul>
                            <div class="tip-box">
                                <strong>💡 Pro Tip:</strong> Document any manual adjustments in the "Allocation Rationale" field for audit trail.
                            </div>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">5</span> Create Child Budgets</h3>
                            <ul>
                                <li>Click <strong>"Create Child Budgets"</strong> button</li>
                                <li>System generates individual budget documents for each allocation</li>
                                <li>Child budgets linked to parent via "Parent Budget" field</li>
                                <li>Each child budget can be independently managed</li>
                            </ul>
                        </div>
                        
                        <div class="step-card">
                            <h3><span class="step-number">6</span> Lock and Finalize</h3>
                            <ul>
                                <li>Set allocation status to "Active" for confirmed allocations</li>
                                <li>Lock allocations to prevent changes: Set "Is Locked" = Yes</li>
                                <li>Add lock reason for compliance</li>
                                <li>Submit parent budget for approval</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>💡 Best Practices</h2>
                        <ul>
                            <li><strong>Data Accuracy:</strong> Validate all