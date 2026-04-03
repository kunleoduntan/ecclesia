# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate, add_months
import json
import numpy as np
from datetime import datetime
from collections import defaultdict

class BudgetPlan(Document):
    def validate(self):
        """Validate budget before saving"""
        self.validate_allocation_percentages()
        self.calculate_totals()
        self.validate_fiscal_year_dates()
        self.set_budget_status()
        
    def before_save(self):
        """Execute before saving"""
        self.update_monthly_totals()
        if self.enable_projection:
            self.apply_projections()
        if self.enable_ai_analysis:
            self.calculate_ai_metrics()
            
    def on_submit(self):
        """Execute on submit"""
        self.create_child_budgets()
        if self.scenario_analysis_enabled:
            self.generate_scenarios()
        if self.create_erpnext_budget:
            self.create_erpnext_budget_records()
        self.send_approval_notifications()
        
    def on_cancel(self):
        """Execute on cancel"""
        self.cancel_child_budgets()
        self.cancel_erpnext_budgets()
        
    # ============================================
    # VALIDATION METHODS
    # ============================================
    
    def validate_allocation_percentages(self):
        """Ensure allocation percentages sum to 100%"""
        if self.allow_branch_split and self.branch_allocations:
            total_branch_pct = sum([flt(d.allocation_percentage) for d in self.branch_allocations])
            if abs(total_branch_pct - 100) > 0.01:
                frappe.throw(_("Branch allocation percentages must sum to 100%. Current total: {0}%").format(total_branch_pct))
                
        if self.allow_cost_center_split and self.cost_center_allocations:
            total_cc_pct = sum([flt(d.allocation_percentage) for d in self.cost_center_allocations])
            if abs(total_cc_pct - 100) > 0.01:
                frappe.throw(_("Cost Center allocation percentages must sum to 100%. Current total: {0}%").format(total_cc_pct))
    
    def validate_fiscal_year_dates(self):
        """Validate fiscal year is set correctly"""
        if self.fiscal_year:
            fy = frappe.get_doc("Fiscal Year", self.fiscal_year)
            if not fy:
                frappe.throw(_("Invalid Fiscal Year"))
                
    def set_budget_status(self):
        """Auto-set budget status based on workflow"""
        if self.docstatus == 0:
            self.budget_status = "Draft"
        elif self.docstatus == 1:
            if self.approval_status == "Approved":
                self.budget_status = "Active"
            else:
                self.budget_status = "Pending Approval"
                
    # ============================================
    # CALCULATION METHODS
    # ============================================
    
    def calculate_totals(self):
        """Calculate grand totals for all monthly budgets"""
        for row in self.monthly_budget:
            row.grand_total = sum([
                flt(row.jan), flt(row.feb), flt(row.mar),
                flt(row.apr), flt(row.may), flt(row.jun),
                flt(row.jul), flt(row.aug), flt(row.sep),
                flt(row.oct), flt(row.nov), flt(row.dec)
            ])
            
    def update_monthly_totals(self):
        """Update totals and percentages"""
        total_budget = sum([flt(d.grand_total) for d in self.monthly_budget])
        
        for row in self.monthly_budget:
            if total_budget > 0:
                row.budget_allocation_percentage = (flt(row.grand_total) / total_budget) * 100
            row.last_updated = now_datetime()
            row.updated_by = frappe.session.user
            
    # ============================================
    # AI & PROJECTION METHODS
    # ============================================
    
    def apply_projections(self):
        """Apply AI-powered projections to budget lines"""
        if not self.projection_method:
            return
            
        for row in self.monthly_budget:
            if row.use_projection:
                projected_values = self.calculate_projection(row)
                self.update_row_with_projections(row, projected_values)
                
    def calculate_projection(self, row):
        """Calculate projections based on method selected"""
        method = self.projection_method
        
        if method == "Historical Average":
            return self.historical_average_projection(row)
        elif method == "Linear Trend":
            return self.linear_trend_projection(row)
        elif method == "Exponential Growth":
            return self.exponential_growth_projection(row)
        elif method == "Moving Average":
            return self.moving_average_projection(row)
        elif method == "ML-Based Prediction":
            return self.ml_based_projection(row)
        else:
            return self.equal_distribution_projection(row)
            
    def historical_average_projection(self, row):
        """Project based on historical averages"""
        if not self.use_historical_data or not row.previous_year_actual:
            return self.equal_distribution_projection(row)
            
        # Get historical data
        historical_data = self.get_historical_data(row.gl_account, row.cost_center)
        
        if not historical_data:
            return self.equal_distribution_projection(row)
            
        # Calculate monthly averages from historical data
        monthly_avg = self.calculate_monthly_averages(historical_data)
        
        # Apply growth rate
        growth_factor = 1 + (flt(self.growth_rate) / 100) if self.growth_rate else 1
        
        projected = {}
        for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
            projected[month] = monthly_avg.get(month, 0) * growth_factor
            
        return projected
        
    def linear_trend_projection(self, row):
        """Project using linear trend analysis"""
        historical_data = self.get_historical_data(row.gl_account, row.cost_center)
        
        if len(historical_data) < 2:
            return self.equal_distribution_projection(row)
            
        # Perform linear regression
        x = np.arange(len(historical_data))
        y = np.array([d['total'] for d in historical_data])
        
        coefficients = np.polyfit(x, y, 1)
        trend_line = np.poly1d(coefficients)
        
        # Project next year
        next_year_total = trend_line(len(historical_data))
        
        # Distribute based on historical monthly patterns
        return self.distribute_by_pattern(next_year_total, historical_data)
        
    def exponential_growth_projection(self, row):
        """Project using exponential growth model"""
        if not row.previous_year_actual:
            return self.equal_distribution_projection(row)
            
        growth_rate = flt(self.growth_rate) / 100 if self.growth_rate else 0.05
        inflation_rate = flt(self.inflation_rate) / 100 if self.inflation_rate else 0.02
        
        combined_rate = (1 + growth_rate) * (1 + inflation_rate)
        projected_total = flt(row.previous_year_actual) * combined_rate
        
        # Get historical pattern
        historical_data = self.get_historical_data(row.gl_account, row.cost_center)
        
        if historical_data and self.seasonality_adjustment:
            return self.distribute_by_pattern(projected_total, historical_data)
        else:
            return self.distribute_equally(projected_total)
            
    def moving_average_projection(self, row):
        """Project using moving average"""
        historical_data = self.get_historical_data(row.gl_account, row.cost_center, years=2)
        
        if len(historical_data) < 2:
            return self.equal_distribution_projection(row)
            
        # Calculate moving average for each month
        monthly_data = defaultdict(list)
        for data in historical_data:
            for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                if month in data:
                    monthly_data[month].append(data[month])
                    
        projected = {}
        for month, values in monthly_data.items():
            projected[month] = sum(values) / len(values)
            
        return projected
        
    def ml_based_projection(self, row):
        """ML-based projection using time series analysis"""
        try:
            from sklearn.linear_model import LinearRegression
            from sklearn.preprocessing import PolynomialFeatures
            
            historical_data = self.get_historical_data(row.gl_account, row.cost_center, years=3)
            
            if len(historical_data) < 12:
                return self.historical_average_projection(row)
                
            # Prepare data for ML model
            X = []
            y = []
            
            for i, data in enumerate(historical_data):
                for month_idx, month in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                    X.append([i * 12 + month_idx, month_idx])
                    y.append(data.get(month, 0))
                    
            X = np.array(X)
            y = np.array(y)
            
            # Train polynomial regression model
            poly_features = PolynomialFeatures(degree=2)
            X_poly = poly_features.fit_transform(X)
            
            model = LinearRegression()
            model.fit(X_poly, y)
            
            # Predict next year
            next_year_idx = len(historical_data)
            projected = {}
            
            for month_idx, month in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                X_pred = np.array([[next_year_idx * 12 + month_idx, month_idx]])
                X_pred_poly = poly_features.transform(X_pred)
                projected[month] = max(0, model.predict(X_pred_poly)[0])
                
            return projected
            
        except Exception as e:
            frappe.log_error(f"ML Projection Error: {str(e)}")
            return self.historical_average_projection(row)
            
    def equal_distribution_projection(self, row):
        """Distribute total equally across months"""
        if row.projection_percentage_local:
            base_amount = flt(row.previous_year_actual) if row.previous_year_actual else flt(row.grand_total)
            projected_total = base_amount * (1 + flt(row.projection_percentage_local) / 100)
        else:
            projected_total = flt(row.grand_total)
            
        return self.distribute_equally(projected_total)
        
    def distribute_equally(self, total):
        """Distribute total equally across 12 months"""
        monthly_amount = total / 12
        return {month: monthly_amount for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']}
        
    def distribute_by_pattern(self, total, historical_data):
        """Distribute based on historical monthly patterns"""
        # Calculate average monthly distribution pattern
        monthly_percentages = defaultdict(float)
        
        for data in historical_data:
            year_total = data.get('total', 1)
            if year_total > 0:
                for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                    monthly_percentages[month] += (data.get(month, 0) / year_total) / len(historical_data)
                    
        # Apply pattern to projected total
        projected = {}
        for month, pct in monthly_percentages.items():
            projected[month] = total * pct
            
        return projected
        
    def update_row_with_projections(self, row, projected_values):
        """Update row with projected values"""
        for month, value in projected_values.items():
            setattr(row, month, value)
            
    def get_historical_data(self, account, cost_center=None, years=None):
        """Fetch historical actuals from GL Entry"""
        if not years:
            years = flt(self.historical_years) if self.historical_years else 3
            
        filters = {
            "account": account,
            "company": self.company,
            "posting_date": [">=", add_months(getdate(), -years * 12)]
        }
        
        if cost_center:
            filters["cost_center"] = cost_center
            
        gl_entries = frappe.get_all(
            "GL Entry",
            filters=filters,
            fields=["posting_date", "debit", "credit"]
        )
        
        # Organize by year and month
        yearly_data = defaultdict(lambda: defaultdict(float))
        
        for entry in gl_entries:
            year = entry.posting_date.year
            month_name = entry.posting_date.strftime("%b").lower()
            amount = flt(entry.debit) - flt(entry.credit)
            yearly_data[year][month_name] += amount
            
        # Convert to list format
        historical_data = []
        for year in sorted(yearly_data.keys()):
            year_data = yearly_data[year].copy()
            year_data['total'] = sum(year_data.values())
            historical_data.append(year_data)
            
        return historical_data
        
    def calculate_monthly_averages(self, historical_data):
        """Calculate average for each month across years"""
        monthly_totals = defaultdict(list)
        
        for data in historical_data:
            for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                if month in data:
                    monthly_totals[month].append(data[month])
                    
        monthly_averages = {}
        for month, values in monthly_totals.items():
            monthly_averages[month] = sum(values) / len(values) if values else 0
            
        return monthly_averages
        
    def calculate_ai_metrics(self):
        """Calculate AI-powered metrics and risk scores"""
        if not self.monthly_budget:
            return
            
        # Calculate risk assessment score
        risk_score = self.calculate_risk_score()
        self.risk_assessment_score = risk_score
        
        # Detect anomalies if enabled
        if self.anomaly_detection:
            self.detect_budget_anomalies()
            
        # Generate recommendations if enabled
        if self.auto_recommendations:
            self.generate_ai_recommendations()
            
    def calculate_risk_score(self):
        """Calculate overall budget risk score (0-100)"""
        risk_factors = []
        
        # Factor 1: Historical variance
        avg_variance = self.get_average_historical_variance()
        risk_factors.append(min(abs(avg_variance), 50))
        
        # Factor 2: Projection confidence
        if self.enable_projection and self.confidence_level:
            risk_factors.append((100 - flt(self.confidence_level)) / 2)
            
        # Factor 3: Budget volatility
        volatility = self.calculate_budget_volatility()
        risk_factors.append(volatility)
        
        # Factor 4: Approval status
        if self.approval_status != "Approved":
            risk_factors.append(20)
            
        # Calculate weighted average
        if risk_factors:
            return sum(risk_factors) / len(risk_factors)
        return 0
        
    def get_average_historical_variance(self):
        """Get average variance from previous budgets"""
        # This would query previous year budgets vs actuals
        # Simplified for now
        return 15.0
        
    def calculate_budget_volatility(self):
        """Calculate monthly volatility score"""
        if len(self.monthly_budget) < 2:
            return 0
            
        monthly_values = []
        for row in self.monthly_budget:
            month_values = [
                flt(row.jan), flt(row.feb), flt(row.mar), flt(row.apr),
                flt(row.may), flt(row.jun), flt(row.jul), flt(row.aug),
                flt(row.sep), flt(row.oct), flt(row.nov), flt(row.dec)
            ]
            if sum(month_values) > 0:
                std_dev = np.std(month_values)
                mean = np.mean(month_values)
                cv = (std_dev / mean * 100) if mean > 0 else 0
                monthly_values.append(cv)
                
        return np.mean(monthly_values) if monthly_values else 0
        
    def detect_budget_anomalies(self):
        """Detect unusual patterns in budget"""
        anomalies = []
        
        for row in self.monthly_budget:
            month_values = [
                flt(row.jan), flt(row.feb), flt(row.mar), flt(row.apr),
                flt(row.may), flt(row.jun), flt(row.jul), flt(row.aug),
                flt(row.sep), flt(row.oct), flt(row.nov), flt(row.dec)
            ]
            
            if len(month_values) < 3:
                continue
                
            mean = np.mean(month_values)
            std_dev = np.std(month_values)
            
            # Check for outliers (values beyond 2 standard deviations)
            for idx, value in enumerate(month_values):
                if abs(value - mean) > 2 * std_dev:
                    anomalies.append({
                        "account": row.gl_account,
                        "month": ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][idx],
                        "value": value,
                        "expected_range": f"{mean - std_dev:.2f} to {mean + std_dev:.2f}"
                    })
                    
        if anomalies:
            frappe.msgprint(
                _("Anomalies detected in budget. Review recommended for: {0}").format(
                    ", ".join([f"{a['account']} ({a['month']})" for a in anomalies[:5]])
                ),
                indicator="orange",
                title=_("Budget Anomalies Detected")
            )
            
    def generate_ai_recommendations(self):
        """Generate AI-powered budget recommendations"""
        recommendations = []
        
        # Recommendation 1: Identify accounts with high variance
        for row in self.monthly_budget:
            if row.ytd_variance_percentage and abs(row.ytd_variance_percentage) > 20:
                recommendations.append(
                    f"Review {row.gl_account}: High variance of {row.ytd_variance_percentage:.1f}%"
                )
                
        # Recommendation 2: Suggest reallocation
        total_budget = sum([flt(d.grand_total) for d in self.monthly_budget])
        for row in self.monthly_budget:
            allocation_pct = (flt(row.grand_total) / total_budget * 100) if total_budget > 0 else 0
            if allocation_pct > 30:
                recommendations.append(
                    f"Consider splitting {row.gl_account}: Represents {allocation_pct:.1f}% of total budget"
                )
                
        if recommendations:
            # Store recommendations in notes
            recommendation_text = "<br>".join(recommendations[:10])
            if not self.budget_notes:
                self.budget_notes = f"<strong>AI Recommendations:</strong><br>{recommendation_text}"
            else:
                self.budget_notes += f"<br><br><strong>AI Recommendations:</strong><br>{recommendation_text}"
                
    # ============================================
    # SCENARIO GENERATION
    # ============================================
    
    def generate_scenarios(self):
        """Auto-generate best/worst case scenarios"""
        self.scenario_budgets = []
        
        # Best Case Scenario
        if self.best_case_percentage:
            self.create_scenario("Best Case", flt(self.best_case_percentage), "green")
            
        # Worst Case Scenario
        if self.worst_case_percentage:
            self.create_scenario("Worst Case", -flt(self.worst_case_percentage), "red")
            
        # Most Likely Scenario (base case)
        self.create_scenario("Most Likely", 0, "blue")
        
    def create_scenario(self, scenario_name, adjustment_pct, color):
        """Create a scenario with adjusted values"""
        scenario = frappe.new_doc("Budget Scenario")
        scenario.scenario_name = scenario_name
        scenario.scenario_type = scenario_name
        scenario.adjustment_percentage = adjustment_pct
        scenario.color_indicator = color.capitalize()
        scenario.is_active = 1
        scenario.created_by_system = 1
        scenario.last_updated = now_datetime()
        
        # Calculate totals
        total_budget = 0
        monthly_totals = defaultdict(float)
        
        for row in self.monthly_budget:
            adjustment_factor = 1 + (adjustment_pct / 100)
            
            for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                adjusted_value = flt(getattr(row, month, 0)) * adjustment_factor
                monthly_totals[month] += adjusted_value
                
        # Set scenario monthly values
        for month, value in monthly_totals.items():
            setattr(scenario, month, value)
            total_budget += value
            
        scenario.total_budget = total_budget
        
        # Calculate variance from base
        base_total = sum([flt(d.grand_total) for d in self.monthly_budget])
        scenario.variance_from_base = total_budget - base_total
        scenario.variance_percentage = ((total_budget - base_total) / base_total * 100) if base_total > 0 else 0
        
        # Set likelihood based on scenario type
        if scenario_name == "Most Likely":
            scenario.likelihood = "High"
            scenario.probability = 70
        elif scenario_name == "Best Case":
            scenario.likelihood = "Medium"
            scenario.probability = 20
        else:  # Worst Case
            scenario.likelihood = "Low"
            scenario.probability = 10
            
        self.append("scenario_budgets", scenario)
        
    # ============================================
    # CHILD BUDGET CREATION
    # ============================================
    
    def create_child_budgets(self):
        """Create child budgets for branches and cost centers"""
        if self.is_group_budget:
            if self.allow_branch_split and self.branch_allocations:
                self.create_branch_budgets()
                
            if self.allow_cost_center_split and self.cost_center_allocations:
                self.create_cost_center_budgets()
                
    def create_branch_budgets(self):
        """Create individual budgets for each branch"""
        for allocation in self.branch_allocations:
            if allocation.child_budget_created:
                continue
                
            # Create child budget
            child_budget = frappe.new_doc("Annual Budget")
            child_budget.company = self.company
            child_budget.fiscal_year = self.fiscal_year
            child_budget.budget_against = "Branch"
            child_budget.branch = allocation.branch
            child_budget.budget_type = self.budget_type
            child_budget.budget_category = self.budget_category
            child_budget.is_group_budget = 0
            child_budget.parent_budget = self.name
            child_budget.currency = self.currency
            
            # Allocate monthly budget items
            allocation_factor = flt(allocation.allocation_percentage) / 100
            
            for row in self.monthly_budget:
                child_row = child_budget.append("monthly_budget", {})
                child_row.gl_account = row.gl_account
                child_row.title = row.title
                child_row.parent_account = row.parent_account
                child_row.branch = allocation.branch
                child_row.fiscal_year = self.fiscal_year
                child_row.company = self.company
                
                # Allocate monthly amounts
                for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                    setattr(child_row, month, flt(getattr(row, month, 0)) * allocation_factor)
                    
            child_budget.insert()
            
            # Update allocation record
            allocation.child_budget_created = 1
            allocation.child_budget_link = child_budget.name
            allocation.created_date = now_datetime()
            
            frappe.msgprint(
                _("Branch budget created: {0}").format(child_budget.name),
                alert=True
            )
            
    def create_cost_center_budgets(self):
        """Create individual budgets for each cost center"""
        for allocation in self.cost_center_allocations:
            if allocation.child_budget_created:
                continue
                
            # Create child budget
            child_budget = frappe.new_doc("Annual Budget")
            child_budget.company = self.company
            child_budget.fiscal_year = self.fiscal_year
            child_budget.budget_against = "Cost Center"
            child_budget.cost_center = allocation.cost_center
            child_budget.budget_type = self.budget_type
            child_budget.budget_category = self.budget_category
            child_budget.is_group_budget = 0
            child_budget.parent_budget = self.name
            child_budget.currency = self.currency
            
            # Allocate monthly budget items
            allocation_factor = flt(allocation.allocation_percentage) / 100
            
            for row in self.monthly_budget:
                child_row = child_budget.append("monthly_budget", {})
                child_row.gl_account = row.gl_account
                child_row.title = row.title
                child_row.parent_account = row.parent_account
                child_row.cost_center = allocation.cost_center
                child_row.fiscal_year = self.fiscal_year
                child_row.company = self.company
                
                # Allocate monthly amounts
                for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                    setattr(child_row, month, flt(getattr(row, month, 0)) * allocation_factor)
                    
            child_budget.insert()
            
            # Update allocation record
            allocation.child_budget_created = 1
            allocation.child_budget_link = child_budget.name
            allocation.created_date = now_datetime()
            
            frappe.msgprint(
                _("Cost Center budget created: {0}").format(child_budget.name),
                alert=True
            )
            
    def cancel_child_budgets(self):
        """Cancel all child budgets"""
        child_budgets = frappe.get_all(
            "Annual Budget",
            filters={"parent_budget": self.name, "docstatus": 1},
            pluck="name"
        )
        
        for child_name in child_budgets:
            try:
                child = frappe.get_doc("Annual Budget", child_name)
                child.cancel()
            except Exception as e:
                frappe.log_error(f"Error cancelling child budget {child_name}: {str(e)}")
                
    # ============================================
    # ERPNEXT BUDGET INTEGRATION
    # ============================================
    
    def create_erpnext_budget_records(self):
        """Create standard ERPNext Budget records"""
        if not self.create_erpnext_budget:
            return
            
        for row in self.monthly_budget:
            # Check if budget already exists
            existing = frappe.db.exists("Budget", {
                "fiscal_year": self.fiscal_year,
                "company": self.company,
                "cost_center": row.cost_center or self.cost_center,
                "budget_against": self.budget_against
            })
            
            if existing:
                continue
                
            # Create ERPNext Budget
            budget = frappe.new_doc("Budget")
            budget.fiscal_year = self.fiscal_year
            budget.company = self.company
            budget.cost_center = row.cost_center or self.cost_center
            budget.budget_against = self.budget_against
            budget.applicable_on_material_request = self.applicable_on_material_request
            budget.applicable_on_purchase_order = self.applicable_on_purchase_order
            budget.applicable_on_booking_actual_expenses = self.applicable_on_booking_actual_expenses
            
            # Add account
            budget.append("accounts", {
                "account": row.gl_account,
                "budget_amount": row.grand_total
            })
            
            budget.insert()
            
    def cancel_erpnext_budgets(self):
        """Cancel ERPNext budgets created from this budget"""
        # Implementation for cancelling ERPNext budgets
        pass
        
    # ============================================
    # NOTIFICATION METHODS
    # ============================================
    
    def send_approval_notifications(self):
        """Send notifications to approvers"""
        if self.requires_approval and self.approver:
            # Send email notification
            frappe.sendmail(
                recipients=[self.approver],
                subject=_("Budget Approval Required: {0}").format(self.name),
                message=self.get_approval_email_content(),
                reference_doctype=self.doctype,
                reference_name=self.name
            )
            
    def get_approval_email_content(self):
        """Get approval email HTML content"""
        total_budget = sum([flt(d.grand_total) for d in self.monthly_budget])
        
        return f"""
        <p>Dear {frappe.db.get_value('User', self.approver, 'full_name')},</p>
        
        <p>A budget requires your approval:</p>
        
        <table border="1" cellpadding="5" style="border-collapse: collapse;">
            <tr><th>Budget Name</th><td>{self.name}</td></tr>
            <tr><th>Company</th><td>{self.company}</td></tr>
            <tr><th>Fiscal Year</th><td>{self.fiscal_year}</td></tr>
            <tr><th>Total Amount</th><td>{frappe.utils.fmt_money(total_budget, currency=self.currency)}</td></tr>
            <tr><th>Status</th><td>{self.budget_status}</td></tr>
        </table>
        
        <p><a href="{frappe.utils.get_url_to_form(self.doctype, self.name)}">Click here to review and approve</a></p>
        """


# ============================================
# WHITELISTED METHODS (API)
# ============================================

@frappe.whitelist()
def auto_allocate_branches(budget_name, method="Equal Distribution"):
    """Auto-allocate budget to branches"""
    budget = frappe.get_doc("Annual Budget", budget_name)
    
    if not budget.allow_branch_split:
        frappe.throw(_("Branch split is not enabled for this budget"))
        
    # Get all active branches for company
    branches = frappe.get_all(
        "Branch",
        filters={"company": budget.company},
        fields=["name", "branch"]
    )
    
    if not branches:
        frappe.throw(_("No branches found for company {0}").format(budget.company))
        
    # Clear existing allocations
    budget.branch_allocations = []
    
    # Calculate allocation based on method
    total_budget = sum([flt(d.grand_total) for d in budget.monthly_budget])
    
    if method == "Equal Distribution":
        allocation_pct = 100 / len(branches)
        allocation_amount = total_budget / len(branches)
        
        for branch in branches:
            budget.append("branch_allocations", {
                "branch": branch.name,
                "allocation_percentage": allocation_pct,
                "allocated_amount": allocation_amount,
                "distribution_method": method,
                "status": "Pending"
            })
            
    elif method == "Proportional (Revenue)":
        # Get revenue for each branch
        branch_revenues = get_branch_revenues(budget.company, budget.fiscal_year)
        total_revenue = sum(branch_revenues.values())
        
        if total_revenue == 0:
            frappe.throw(_("No revenue data found for proportional allocation"))
            
        for branch in branches:
            revenue = branch_revenues.get(branch.name, 0)
            allocation_pct = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            allocation_amount = total_budget * (allocation_pct / 100)
            
            budget.append("branch_allocations", {
                "branch": branch.name,
                "allocation_percentage": allocation_pct,
                "allocated_amount": allocation_amount,
                "revenue_share": revenue,
                "distribution_method": method,
                "status": "Pending"
            })
            
    elif method == "Proportional (Headcount)":
        # Get headcount for each branch
        branch_headcounts = get_branch_headcounts(budget.company)
        total_headcount = sum(branch_headcounts.values())
        
        if total_headcount == 0:
            frappe.throw(_("No headcount data found for proportional allocation"))
            
        for branch in branches:
            headcount = branch_headcounts.get(branch.name, 0)
            allocation_pct = (headcount / total_headcount * 100) if total_headcount > 0 else 0
            allocation_amount = total_budget * (allocation_pct / 100)
            
            budget.append("branch_allocations", {
                "branch": branch.name,
                "allocation_percentage": allocation_pct,
                "allocated_amount": allocation_amount,
                "headcount": headcount,
                "distribution_method": method,
                "status": "Pending"
            })
            
    budget.save()
    
    frappe.msgprint(
        _("Branch allocation completed using {0} method").format(method),
        alert=True,
        indicator="green"
    )
    
    return budget


@frappe.whitelist()
def auto_allocate_cost_centers(budget_name, method="Equal Distribution"):
    """Auto-allocate budget to cost centers"""
    budget = frappe.get_doc("Annual Budget", budget_name)
    
    if not budget.allow_cost_center_split:
        frappe.throw(_("Cost center split is not enabled for this budget"))
        
    # Get all cost centers for company
    cost_centers = frappe.get_all(
        "Cost Center",
        filters={"company": budget.company, "is_group": 0},
        fields=["name", "cost_center_name"]
    )
    
    if not cost_centers:
        frappe.throw(_("No cost centers found for company {0}").format(budget.company))
        
    # Clear existing allocations
    budget.cost_center_allocations = []
    
    # Calculate allocation
    total_budget = sum([flt(d.grand_total) for d in budget.monthly_budget])
    
    if method == "Equal Distribution":
        allocation_pct = 100 / len(cost_centers)
        allocation_amount = total_budget / len(cost_centers)
        
        for cc in cost_centers:
            budget.append("cost_center_allocations", {
                "cost_center": cc.name,
                "allocation_percentage": allocation_pct,
                "allocated_amount": allocation_amount,
                "distribution_method": method,
                "status": "Pending"
            })
            
    budget.save()
    
    frappe.msgprint(
        _("Cost center allocation completed using {0} method").format(method),
        alert=True,
        indicator="green"
    )
    
    return budget


@frappe.whitelist()
def apply_projection_to_all(budget_name):
    """Apply projection to all budget lines"""
    budget = frappe.get_doc("Annual Budget", budget_name)
    
    if not budget.enable_projection:
        frappe.throw(_("Projection is not enabled for this budget"))
        
    # Enable projection for all lines
    for row in budget.monthly_budget:
        row.use_projection = 1
        
    budget.apply_projections()
    budget.save()
    
    frappe.msgprint(
        _("Projections applied to all budget lines"),
        alert=True,
        indicator="green"
    )
    
    return budget


@frappe.whitelist()
def calculate_variance_analysis(budget_name):
    """Calculate variance analysis for budget"""
    budget = frappe.get_doc("Annual Budget", budget_name)
    
    for row in budget.monthly_budget:
        # Get actuals from GL Entry
        ytd_actual = get_ytd_actual(
            row.gl_account,
            row.cost_center,
            budget.fiscal_year,
            budget.company
        )
        
        # Calculate YTD budget (sum up to current month)
        current_month = datetime.now().month
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        ytd_budget = sum([flt(getattr(row, months[i], 0)) for i in range(current_month)])
        
        # Calculate variance
        row.ytd_actual = ytd_actual
        row.ytd_variance = ytd_actual - ytd_budget
        row.ytd_variance_percentage = ((ytd_actual - ytd_budget) / ytd_budget * 100) if ytd_budget > 0 else 0
        
        # Calculate projected year-end
        if current_month > 0:
            monthly_avg_actual = ytd_actual / current_month
            row.projected_year_end = monthly_avg_actual * 12
            
        # Calculate forecast accuracy
        if ytd_budget > 0:
            row.forecast_accuracy = 100 - abs(row.ytd_variance_percentage)
            
    budget.save()
    
    frappe.msgprint(
        _("Variance analysis completed"),
        alert=True,
        indicator="green"
    )
    
    return budget


@frappe.whitelist()
def export_to_excel(budget_name):
    """Export budget to formatted Excel"""
    from frappe.utils.xlsxutils import make_xlsx
    import io
    
    budget = frappe.get_doc("Annual Budget", budget_name)
    
    # Prepare data
    data = []
    
    # Header
    data.append(["Annual Budget Report"])
    data.append([])
    data.append(["Company:", budget.company])
    data.append(["Fiscal Year:", budget.fiscal_year])
    data.append(["Budget Type:", budget.budget_type])
    data.append([])
    
    # Column headers
    data.append([
        "Account", "Title", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Total"
    ])
    
    # Data rows
    for row in budget.monthly_budget:
        data.append([
            row.gl_account, row.title,
            row.jan, row.feb, row.mar, row.apr, row.may, row.jun,
            row.jul, row.aug, row.sep, row.oct, row.nov, row.dec,
            row.grand_total
        ])
        
    # Create Excel file
    xlsx_file = make_xlsx(data, "Budget Report")
    
    frappe.response["filename"] = f"{budget.name}.xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_branch_revenues(company, fiscal_year):
    """Get revenue by branch"""
    # Query GL Entry or Sales Invoice for revenue by branch
    revenues = frappe.db.sql("""
        SELECT branch, SUM(base_grand_total) as revenue
        FROM `tabSales Invoice`
        WHERE company = %s
        AND docstatus = 1
        AND posting_date BETWEEN (SELECT year_start_date FROM `tabFiscal Year` WHERE name = %s)
        AND (SELECT year_end_date FROM `tabFiscal Year` WHERE name = %s)
        GROUP BY branch
    """, (company, fiscal_year, fiscal_year), as_dict=1)
    
    return {r.branch: flt(r.revenue) for r in revenues}


def get_branch_headcounts(company):
    """Get headcount by branch"""
    headcounts = frappe.db.sql("""
        SELECT branch, COUNT(*) as headcount
        FROM `tabEmployee`
        WHERE company = %s
        AND status = 'Active'
        GROUP BY branch
    """, company, as_dict=1)
    
    return {h.branch: h.headcount for h in headcounts}


def get_ytd_actual(account, cost_center, fiscal_year, company):
    """Get YTD actual from GL Entry"""
    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    
    filters = {
        "account": account,
        "company": company,
        "posting_date": ["between", [fy.year_start_date, datetime.now().date()]]
    }
    
    if cost_center:
        filters["cost_center"] = cost_center
        
    gl_entries = frappe.get_all(
        "GL Entry",
        filters=filters,
        fields=["SUM(debit - credit) as total"]
    )
    
    return flt(gl_entries[0].total) if gl_entries else 0





# Copyright (c) 2025, Omnibiz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, add_months, get_first_day, get_last_day
import json
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression


class AnnualBudget(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_totals()
        self.validate_allocations()
        
    def validate_dates(self):
        if getdate(self.start_date) >= getdate(self.end_date):
            frappe.throw(_("End Date must be greater than Start Date"))
    
    def calculate_totals(self):
        """Calculate total budget from monthly budget items"""
        total = 0
        for row in self.monthly_budget:
            row_total = sum([
                flt(row.jan), flt(row.feb), flt(row.mar),
                flt(row.apr), flt(row.may), flt(row.jun),
                flt(row.jul), flt(row.aug), flt(row.sep),
                flt(row.oct), flt(row.nov), flt(row.dec)
            ])
            row.total = row_total
            total += row_total
        
        self.total_budget = total
    
    def validate_allocations(self):
        """Validate branch and cost center allocations"""
        if self.is_group_budget and self.allow_branch_split:
            total_branch_pct = sum([flt(d.allocation_percentage) for d in self.branch_allocations])
            if total_branch_pct > 100:
                frappe.throw(_("Total Branch Allocation cannot exceed 100%"))
        
        if self.is_group_budget and self.allow_cost_center_split:
            total_cc_pct = sum([flt(d.allocation_percentage) for d in self.cost_center_allocations])
            if total_cc_pct > 100:
                frappe.throw(_("Total Cost Center Allocation cannot exceed 100%"))


# ==================== WHITELISTED METHODS ====================

@frappe.whitelist()
def copy_from_previous_budget(source_budget, target_budget, apply_growth=False, growth_rate=0):
    """
    Copy budget data from a previous budget to a new one
    
    Args:
        source_budget: Name of the source budget document
        target_budget: Name of the target budget document
        apply_growth: Boolean to apply growth rate
        growth_rate: Growth rate percentage to apply
    """
    try:
        # Get source budget
        source = frappe.get_doc("Annual Budget", source_budget)
        target = frappe.get_doc("Annual Budget", target_budget)
        
        # Clear existing monthly budget items
        target.monthly_budget = []
        
        growth_multiplier = 1 + (flt(growth_rate) / 100) if apply_growth else 1
        
        # Copy monthly budget items
        for source_row in source.monthly_budget:
            target.append("monthly_budget", {
                "gl_account": source_row.gl_account,
                "cost_center": source_row.cost_center,
                "branch": source_row.branch,
                "jan": flt(source_row.jan) * growth_multiplier,
                "feb": flt(source_row.feb) * growth_multiplier,
                "mar": flt(source_row.mar) * growth_multiplier,
                "apr": flt(source_row.apr) * growth_multiplier,
                "may": flt(source_row.may) * growth_multiplier,
                "jun": flt(source_row.jun) * growth_multiplier,
                "jul": flt(source_row.jul) * growth_multiplier,
                "aug": flt(source_row.aug) * growth_multiplier,
                "sep": flt(source_row.sep) * growth_multiplier,
                "oct": flt(source_row.oct) * growth_multiplier,
                "nov": flt(source_row.nov) * growth_multiplier,
                "dec": flt(source_row.dec) * growth_multiplier,
            })
        
        target.save()
        
        return {
            "success": True,
            "message": _("Budget copied successfully from {0}").format(source_budget),
            "lines_copied": len(target.monthly_budget)
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Copy Budget Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def generate_projections(budget_name, projection_method="Historical Average", historical_years=3, growth_rate=5):
    """
    Generate budget projections based on historical data
    
    Args:
        budget_name: Name of the budget document
        projection_method: Method to use for projection
        historical_years: Number of years to analyze
        growth_rate: Growth rate percentage
    """
    try:
        budget = frappe.get_doc("Annual Budget", budget_name)
        
        if projection_method == "Historical Average":
            return generate_historical_average_projection(budget, int(historical_years))
        elif projection_method == "Linear Trend":
            return generate_linear_trend_projection(budget, int(historical_years))
        elif projection_method == "Growth Rate":
            return apply_growth_rate_projection(budget, flt(growth_rate))
        else:
            return generate_historical_average_projection(budget, int(historical_years))
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Projection Error")
        return {
            "success": False,
            "message": str(e)
        }


def generate_historical_average_projection(budget, years=3):
    """Generate projections based on historical average"""
    try:
        company = budget.company
        start_date = getdate(budget.start_date)
        
        projections = []
        
        for row in budget.monthly_budget:
            # Get historical actuals
            historical_data = frappe.db.sql("""
                SELECT 
                    MONTH(posting_date) as month,
                    AVG(debit - credit) as avg_amount
                FROM `tabGL Entry`
                WHERE 
                    company = %(company)s
                    AND account = %(account)s
                    AND cost_center = %(cost_center)s
                    AND posting_date >= DATE_SUB(%(start_date)s, INTERVAL %(years)s YEAR)
                    AND posting_date < %(start_date)s
                GROUP BY MONTH(posting_date)
            """, {
                "company": company,
                "account": row.gl_account,
                "cost_center": row.cost_center or "",
                "start_date": start_date,
                "years": years
            }, as_dict=True)
            
            # Create month mapping
            month_avg = {d.month: flt(d.avg_amount) for d in historical_data}
            
            # Apply to budget
            months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            for idx, month in enumerate(months, 1):
                if idx in month_avg:
                    row.set(month, month_avg[idx])
            
            projections.append({
                "account": row.gl_account,
                "projected": True
            })
        
        budget.save()
        
        return {
            "success": True,
            "message": _("Projections generated successfully"),
            "method": "Historical Average",
            "accounts_projected": len(projections)
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Historical Average Projection Error")
        raise


def generate_linear_trend_projection(budget, years=3):
    """Generate projections using linear regression"""
    try:
        company = budget.company
        start_date = getdate(budget.start_date)
        
        for row in budget.monthly_budget:
            # Get historical monthly data
            historical_data = frappe.db.sql("""
                SELECT 
                    DATE_FORMAT(posting_date, '%Y-%m') as period,
                    SUM(debit - credit) as amount
                FROM `tabGL Entry`
                WHERE 
                    company = %(company)s
                    AND account = %(account)s
                    AND cost_center = %(cost_center)s
                    AND posting_date >= DATE_SUB(%(start_date)s, INTERVAL %(years)s YEAR)
                    AND posting_date < %(start_date)s
                GROUP BY DATE_FORMAT(posting_date, '%Y-%m')
                ORDER BY posting_date
            """, {
                "company": company,
                "account": row.gl_account,
                "cost_center": row.cost_center or "",
                "start_date": start_date,
                "years": years
            }, as_dict=True)
            
            if len(historical_data) > 3:
                # Prepare data for linear regression
                X = np.array(range(len(historical_data))).reshape(-1, 1)
                y = np.array([flt(d.amount) for d in historical_data])
                
                # Fit linear model
                model = LinearRegression()
                model.fit(X, y)
                
                # Project next 12 months
                future_X = np.array(range(len(historical_data), len(historical_data) + 12)).reshape(-1, 1)
                projections = model.predict(future_X)
                
                # Apply to budget
                months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                for idx, month in enumerate(months):
                    row.set(month, max(0, projections[idx]))  # Ensure non-negative
        
        budget.save()
        
        return {
            "success": True,
            "message": _("Linear trend projections generated successfully"),
            "method": "Linear Trend"
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Linear Trend Projection Error")
        raise


def apply_growth_rate_projection(budget, growth_rate):
    """Apply simple growth rate to existing budget"""
    try:
        multiplier = 1 + (flt(growth_rate) / 100)
        
        for row in budget.monthly_budget:
            months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            for month in months:
                current_value = flt(row.get(month))
                row.set(month, current_value * multiplier)
        
        budget.save()
        
        return {
            "success": True,
            "message": _("Growth rate of {0}% applied successfully").format(growth_rate),
            "method": "Growth Rate"
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Growth Rate Projection Error")
        raise


@frappe.whitelist()
def split_budget_by_branches(budget_name, distribution_method="Equal Distribution"):
    """
    Split group budget into branch-specific budgets
    
    Args:
        budget_name: Name of the budget document
        distribution_method: Method to use for distribution
    """
    try:
        budget = frappe.get_doc("Annual Budget", budget_name)
        
        if not budget.is_group_budget or not budget.allow_branch_split:
            return {
                "success": False,
                "message": _("This budget is not configured for branch splitting")
            }
        
        if not budget.branch_allocations:
            return {
                "success": False,
                "message": _("No branch allocations defined")
            }
        
        created_budgets = []
        
        for branch_alloc in budget.branch_allocations:
            # Create child budget for branch
            child_budget = frappe.new_doc("Annual Budget")
            child_budget.budget_name = f"{budget.budget_name} - {branch_alloc.branch_name}"
            child_budget.company = budget.company
            child_budget.fiscal_year = budget.fiscal_year
            child_budget.start_date = budget.start_date
            child_budget.end_date = budget.end_date
            child_budget.branch = branch_alloc.branch
            child_budget.is_group_budget = 0
            child_budget.parent_budget = budget.name
            
            # Copy and allocate monthly budget items
            for row in budget.monthly_budget:
                allocation_factor = flt(branch_alloc.allocation_percentage) / 100
                
                child_budget.append("monthly_budget", {
                    "gl_account": row.gl_account,
                    "cost_center": row.cost_center,
                    "branch": branch_alloc.branch,
                    "jan": flt(row.jan) * allocation_factor,
                    "feb": flt(row.feb) * allocation_factor,
                    "mar": flt(row.mar) * allocation_factor,
                    "apr": flt(row.apr) * allocation_factor,
                    "may": flt(row.may) * allocation_factor,
                    "jun": flt(row.jun) * allocation_factor,
                    "jul": flt(row.jul) * allocation_factor,
                    "aug": flt(row.aug) * allocation_factor,
                    "sep": flt(row.sep) * allocation_factor,
                    "oct": flt(row.oct) * allocation_factor,
                    "nov": flt(row.nov) * allocation_factor,
                    "dec": flt(row.dec) * allocation_factor,
                })
            
            child_budget.insert()
            created_budgets.append(child_budget.name)
            
            # Update branch allocation tracking
            branch_alloc.child_budget_created = 1
            branch_alloc.child_budget_link = child_budget.name
        
        budget.save()
        
        return {
            "success": True,
            "message": _("Created {0} branch budgets successfully").format(len(created_budgets)),
            "budgets": created_budgets
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Budget Split Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def split_budget_by_cost_centers(budget_name, distribution_method="Equal Distribution"):
    """
    Split group budget into cost center-specific budgets
    
    Args:
        budget_name: Name of the budget document
        distribution_method: Method to use for distribution
    """
    try:
        budget = frappe.get_doc("Annual Budget", budget_name)
        
        if not budget.is_group_budget or not budget.allow_cost_center_split:
            return {
                "success": False,
                "message": _("This budget is not configured for cost center splitting")
            }
        
        if not budget.cost_center_allocations:
            return {
                "success": False,
                "message": _("No cost center allocations defined")
            }
        
        created_budgets = []
        
        for cc_alloc in budget.cost_center_allocations:
            # Create child budget for cost center
            child_budget = frappe.new_doc("Annual Budget")
            child_budget.budget_name = f"{budget.budget_name} - {cc_alloc.cost_center_name}"
            child_budget.company = budget.company
            child_budget.fiscal_year = budget.fiscal_year
            child_budget.start_date = budget.start_date
            child_budget.end_date = budget.end_date
            child_budget.cost_center = cc_alloc.cost_center
            child_budget.is_group_budget = 0
            child_budget.parent_budget = budget.name
            
            # Copy and allocate monthly budget items
            for row in budget.monthly_budget:
                allocation_factor = flt(cc_alloc.allocation_percentage) / 100
                
                child_budget.append("monthly_budget", {
                    "gl_account": row.gl_account,
                    "cost_center": cc_alloc.cost_center,
                    "branch": row.branch,
                    "jan": flt(row.jan) * allocation_factor,
                    "feb": flt(row.feb) * allocation_factor,
                    "mar": flt(row.mar) * allocation_factor,
                    "apr": flt(row.apr) * allocation_factor,
                    "may": flt(row.may) * allocation_factor,
                    "jun": flt(row.jun) * allocation_factor,
                    "jul": flt(row.jul) * allocation_factor,
                    "aug": flt(row.aug) * allocation_factor,
                    "sep": flt(row.sep) * allocation_factor,
                    "oct": flt(row.oct) * allocation_factor,
                    "nov": flt(row.nov) * allocation_factor,
                    "dec": flt(row.dec) * allocation_factor,
                })
            
            child_budget.insert()
            created_budgets.append(child_budget.name)
            
            # Update cost center allocation tracking
            cc_alloc.child_budget_created = 1
            cc_alloc.child_budget_link = child_budget.name
        
        budget.save()
        
        return {
            "success": True,
            "message": _("Created {0} cost center budgets successfully").format(len(created_budgets)),
            "budgets": created_budgets
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Budget Split Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def calculate_variance(budget_name):
    """
    Calculate variance between budget and actuals
    
    Args:
        budget_name: Name of the budget document
    """
    try:
        budget = frappe.get_doc("Annual Budget", budget_name)
        company = budget.company
        
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        current_month = datetime.now().month
        
        for row in budget.monthly_budget:
            ytd_budget = 0
            ytd_actual = 0
            
            for month_idx in range(1, current_month + 1):
                month_name = months[month_idx - 1]
                ytd_budget += flt(row.get(month_name))
                
                # Get actual for this month
                month_start = get_first_day(add_months(budget.start_date, month_idx - 1))
                month_end = get_last_day(add_months(budget.start_date, month_idx - 1))
                
                actual = frappe.db.sql("""
                    SELECT SUM(debit - credit) as amount
                    FROM `tabGL Entry`
                    WHERE 
                        company = %(company)s
                        AND account = %(account)s
                        AND cost_center = %(cost_center)s
                        AND posting_date BETWEEN %(start)s AND %(end)s
                """, {
                    "company": company,
                    "account": row.gl_account,
                    "cost_center": row.cost_center or "",
                    "start": month_start,
                    "end": month_end
                }, as_dict=True)
                
                ytd_actual += flt(actual[0].amount) if actual else 0
            
            # Update variance fields
            row.ytd_actual = ytd_actual
            row.ytd_variance = ytd_actual - ytd_budget
            row.ytd_variance_percentage = (row.ytd_variance / ytd_budget * 100) if ytd_budget else 0
        
        budget.save()
        
        return {
            "success": True,
            "message": _("Variance calculated successfully")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Variance Calculation Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def generate_scenarios(budget_name, best_case_pct=20, worst_case_pct=20):
    """
    Generate best and worst case scenarios
    
    Args:
        budget_name: Name of the budget document
        best_case_pct: Percentage increase for best case
        worst_case_pct: Percentage decrease for worst case
    """
    try:
        budget = frappe.get_doc("Annual Budget", budget_name)
        
        # Clear existing scenarios
        budget.scenarios = []
        
        # Generate Best Case Scenario
        best_case = budget.append("scenarios", {})
        best_case.scenario_name = "Best Case Scenario"
        best_case.scenario_type = "Best Case"
        best_case.adjustment_percentage = flt(best_case_pct)
        best_case.description = f"Optimistic projection with {best_case_pct}% increase"
        best_case.probability = 25
        best_case.is_active = 1
        best_case.color_indicator = "Green"
        
        # Generate Worst Case Scenario
        worst_case = budget.append("scenarios", {})
        worst_case.scenario_name = "Worst Case Scenario"
        worst_case.scenario_type = "Worst Case"
        worst_case.adjustment_percentage = -flt(worst_case_pct)
        worst_case.description = f"Conservative projection with {worst_case_pct}% decrease"
        worst_case.probability = 15
        worst_case.is_active = 1
        worst_case.color_indicator = "Red"
        
        # Generate Most Likely Scenario
        most_likely = budget.append("scenarios", {})
        most_likely.scenario_name = "Most Likely Scenario"
        most_likely.scenario_type = "Most Likely"
        most_likely.adjustment_percentage = 0
        most_likely.description = "Base case projection"
        most_likely.probability = 60
        most_likely.is_active = 1
        most_likely.color_indicator = "Blue"
        
        # Calculate scenario values
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        
        for scenario in budget.scenarios:
            multiplier = 1 + (flt(scenario.adjustment_percentage) / 100)
            total = 0
            
            for month in months:
                month_total = sum([flt(row.get(month)) for row in budget.monthly_budget])
                scenario.set(month, month_total * multiplier)
                total += month_total * multiplier
            
            scenario.total_budget = total
            scenario.variance_from_base = total - budget.total_budget
            scenario.variance_percentage = (scenario.variance_from_base / budget.total_budget * 100) if budget.total_budget else 0
        
        budget.save()
        
        return {
            "success": True,
            "message": _("Scenarios generated successfully"),
            "scenarios_created": len(budget.scenarios)
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Scenario Generation Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def auto_distribute_branches(budget_name, method="Equal Distribution"):
    """
    Automatically distribute budget across branches based on selected method
    
    Args:
        budget_name: Name of the budget document
        method: Distribution method to use
    """
    try:
        budget = frappe.get_doc("Annual Budget", budget_name)
        branches = frappe.get_all("Branch", filters={"company": budget.company}, fields=["name", "branch"])
        
        if not branches:
            return {
                "success": False,
                "message": _("No branches found for this company")
            }
        
        budget.branch_allocations = []
        
        if method == "Equal Distribution":
            allocation_pct = 100 / len(branches)
            allocation_amt = budget.total_budget / len(branches)
            
            for branch in branches:
                budget.append("branch_allocations", {
                    "branch": branch.name,
                    "allocation_percentage": allocation_pct,
                    "allocated_amount": allocation_amt,
                    "distribution_method": method,
                    "status": "Pending"
                })
        
        budget.save()
        
        return {
            "success": True,
            "message": _("Budget distributed across {0} branches").format(len(branches)),
            "method": method
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Auto Distribution Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_budget_summary(budget_name):
    """
    Get comprehensive budget summary with analytics
    
    Args:
        budget_name: Name of the budget document
    """
    try:
        budget = frappe.get_doc("Annual Budget", budget_name)
        
        summary = {
            "budget_name": budget.budget_name,
            "company": budget.company,
            "fiscal_year": budget.fiscal_year,
            "total_budget": budget.total_budget,
            "status": budget.budget_status,
            "is_group": budget.is_group_budget,
            "branch_count": len(budget.branch_allocations) if budget.branch_allocations else 0,
            "cost_center_count": len(budget.cost_center_allocations) if budget.cost_center_allocations else 0,
            "scenario_count": len(budget.scenarios) if budget.scenarios else 0,
            "monthly_breakdown": {},
            "account_breakdown": []
        }
        
        # Monthly breakdown
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        for month in months:
            summary["monthly_breakdown"][month] = sum([flt(row.get(month)) for row in budget.monthly_budget])
        
        # Account-wise breakdown
        for row in budget.monthly_budget:
            summary["account_breakdown"].append({
                "account": row.gl_account,
                "cost_center": row.cost_center,
                "total": row.total
            })
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Budget Summary Error")
        return {
            "success": False,
            "message": str(e)
        }



# ============================================
# EXCEL IMPORT FUNCTIONALITY
# ============================================

@frappe.whitelist()
def get_excel_import_template(budget_name):
    """Generate Excel template for budget import"""
    from frappe.utils.xlsxutils import make_xlsx
    import io
    
    budget = frappe.get_doc("Budget Plan", budget_name)
    
    # Prepare template data
    data = []
    
    # Instructions sheet
    instructions = [
        ["BUDGET IMPORT TEMPLATE"],
        [""],
        ["Instructions:"],
        ["1. Fill in the GL Account column with valid account codes"],
        ["2. Enter monthly budget amounts in the corresponding month columns"],
        ["3. Cost Center and Branch are optional"],
        ["4. Do not modify the header row"],
        ["5. Save and upload this file back to the system"],
        [""],
        ["Company:", budget.company],
        ["Fiscal Year:", budget.fiscal_year],
        ["Currency:", budget.currency],
        [""],
        ["BUDGET DATA - Start entering data below the header row"],
        ["GL Account", "Account Name", "Cost Center", "Branch", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Notes"],
        ["Example: 5000", "Example: Operating Expenses", "Main - XYZ", "", "10000", "10000", "10000", "10000", "10000", "10000", "10000", "10000", "10000", "10000", "10000", "10000", "Sample entry"]
    ]
    
    # Add existing budget lines if any
    if budget.monthly_budget:
        for row in budget.monthly_budget:
            instructions.append([
                row.gl_account or "",
                row.title or "",
                row.cost_center or "",
                row.branch or "",
                flt(row.jan), flt(row.feb), flt(row.mar),
                flt(row.apr), flt(row.may), flt(row.jun),
                flt(row.jul), flt(row.aug), flt(row.sep),
                flt(row.oct), flt(row.nov), flt(row.dec),
                row.notes or ""
            ])
    
    # Create Excel file
    xlsx_file = make_xlsx(instructions, "Budget Import Template")
    
    frappe.response["filename"] = f"Budget_Import_Template_{budget.name}.xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"


@frappe.whitelist()
def process_excel_import(budget_name, file_url):
    """Process uploaded Excel file and import budget data"""
    import openpyxl
    from frappe.utils.file_manager import get_file
    import os
    
    try:
        budget = frappe.get_doc("Budget Plan", budget_name)
        
        if budget.docstatus == 1:
            frappe.throw(_("Cannot import to a submitted budget"))
        
        # Get file content
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()
        
        # Load workbook
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        
        # Find header row (should contain "GL Account")
        header_row = None
        for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
            if row and "GL Account" in str(row[0]):
                header_row = idx
                break
        
        if not header_row:
            frappe.throw(_("Could not find header row. Please ensure the template format is correct."))
        
        # Get headers
        headers = [cell.value for cell in ws[header_row]]
        
        # Validate required columns
        required_cols = ["GL Account", "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        for req_col in required_cols:
            if req_col not in headers:
                frappe.throw(_("Missing required column: {0}").format(req_col))
        
        # Build column mapping
        col_map = {}
        for idx, header in enumerate(headers):
            if header:
                col_map[header] = idx
        
        # Clear existing budget lines
        budget.monthly_budget = []
        
        # Import data
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
            try:
                # Skip empty rows
                if not row or not row[col_map.get("GL Account")]:
                    continue
                
                gl_account = str(row[col_map["GL Account"]]).strip()
                
                # Skip example rows
                if "example" in gl_account.lower():
                    skipped_count += 1
                    continue
                
                # Validate GL Account exists
                if not frappe.db.exists("Account", gl_account):
                    errors.append(f"Row {row_idx}: Account '{gl_account}' does not exist")
                    skipped_count += 1
                    continue
                
                # Get account details
                account_details = frappe.db.get_value("Account", gl_account, 
                    ["account_name", "account_type", "root_type"], as_dict=True)
                
                # Create budget line
                budget_line = budget.append("monthly_budget", {})
                budget_line.gl_account = gl_account
                budget_line.title = row[col_map.get("Account Name")] or account_details.account_name
                budget_line.cost_center = row[col_map.get("Cost Center")] or budget.cost_center
                budget_line.branch = row[col_map.get("Branch")] or budget.branch
                budget_line.fiscal_year = budget.fiscal_year
                budget_line.company = budget.company
                
                # Set monthly values
                months = {
                    "Jan": "jan", "Feb": "feb", "Mar": "mar", "Apr": "apr",
                    "May": "may", "Jun": "jun", "Jul": "jul", "Aug": "aug",
                    "Sep": "sep", "Oct": "oct", "Nov": "nov", "Dec": "dec"
                }
                
                for excel_month, db_month in months.items():
                    if excel_month in col_map:
                        value = row[col_map[excel_month]]
                        setattr(budget_line, db_month, flt(value) if value else 0)
                
                # Set notes if available
                if "Notes" in col_map and row[col_map["Notes"]]:
                    budget_line.notes = str(row[col_map["Notes"]])
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")
                skipped_count += 1
                continue
        
        # Save budget
        budget.save()
        
        # Prepare result message
        message = f"✅ Import completed successfully!<br><br>"
        message += f"📊 <strong>Imported:</strong> {imported_count} budget lines<br>"
        
        if skipped_count > 0:
            message += f"⚠️ <strong>Skipped:</strong> {skipped_count} rows<br>"
        
        if errors:
            message += "<br><strong>Errors:</strong><br>"
            for error in errors[:10]:  # Show first 10 errors
                message += f"• {error}<br>"
            
            if len(errors) > 10:
                message += f"<br>...and {len(errors) - 10} more errors"
        
        return {
            "success": True,
            "message": message,
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Excel Import Error")
        return {
            "success": False,
            "message": f"❌ Import failed: {str(e)}",
            "imported": 0,
            "skipped": 0,
            "errors": [str(e)]
        }


@frappe.whitelist()
def validate_import_file(file_url):
    """Validate uploaded Excel file before import"""
    import openpyxl
    
    try:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()
        
        # Check file extension
        if not file_path.endswith(('.xlsx', '.xls')):
            return {
                "valid": False,
                "message": "❌ Invalid file format. Please upload an Excel file (.xlsx or .xls)"
            }
        
        # Try to load workbook
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        
        # Check for header row
        header_found = False
        row_count = 0
        
        for row in ws.iter_rows(min_row=1, max_row=20, values_only=True):
            row_count += 1
            if row and "GL Account" in str(row[0]):
                header_found = True
                break
        
        if not header_found:
            return {
                "valid": False,
                "message": "❌ Invalid template. Could not find 'GL Account' header column."
            }
        
        # Count data rows
        data_rows = sum(1 for row in ws.iter_rows(min_row=row_count + 1, values_only=True) 
                       if row and row[0])
        
        return {
            "valid": True,
            "message": f"✅ Valid template found with approximately {data_rows} data rows",
            "rows": data_rows
        }
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"❌ Error reading file: {str(e)}"
        }
        
        
# ============================================
# ADVANCED EXCEL EXPORT WITH FORMATTING
# ============================================

@frappe.whitelist()
def export_to_excel_advanced(budget_name, export_type="Standard", include_charts=1, include_summary=1):
    """
    Export budget to beautifully formatted Excel with colors, charts, and formatting
    
    Args:
        budget_name: Budget document name
        export_type: Standard/Detailed/Variance/With Scenarios
        include_charts: Whether to include charts
        include_summary: Whether to include summary sheet
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, LineChart, Reference, PieChart
    from openpyxl.utils import get_column_letter
    import io
    from datetime import datetime
    
    try:
        budget = frappe.get_doc("Budget Plan", budget_name)
        
        # Create workbook
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default sheet
        
        # Color scheme
        colors = {
            'primary': '667eea',      # Purple
            'secondary': '764ba2',    # Deep purple
            'success': '28a745',      # Green
            'warning': 'ffc107',      # Yellow
            'danger': 'dc3545',       # Red
            'info': '17a2b8',         # Cyan
            'light': 'f8f9fa',        # Light gray
            'dark': '343a40',         # Dark gray
            'white': 'ffffff'
        }
        
        # Define styles
        header_fill = PatternFill(start_color=colors['primary'], end_color=colors['primary'], fill_type='solid')
        header_font = Font(name='Calibri', size=12, bold=True, color=colors['white'])
        subheader_fill = PatternFill(start_color=colors['secondary'], end_color=colors['secondary'], fill_type='solid')
        subheader_font = Font(name='Calibri', size=11, bold=True, color=colors['white'])
        
        title_font = Font(name='Calibri', size=16, bold=True, color=colors['primary'])
        normal_font = Font(name='Calibri', size=10)
        bold_font = Font(name='Calibri', size=10, bold=True)
        
        currency_format = '#,##0.00'
        percent_format = '0.00%'
        
        center_align = Alignment(horizontal='center', vertical='center')
        right_align = Alignment(horizontal='right', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')
        
        thin_border = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )
        
        # ============================================
        # SUMMARY SHEET
        # ============================================
        if int(include_summary):
            ws_summary = wb.create_sheet("📊 Summary", 0)
            
            # Title
            ws_summary.merge_cells('A1:F1')
            cell = ws_summary['A1']
            cell.value = f"📊 Budget Summary: {budget.name}"
            cell.font = Font(name='Calibri', size=18, bold=True, color=colors['primary'])
            cell.alignment = center_align
            ws_summary.row_dimensions[1].height = 30
            
            # Budget info section
            row = 3
            info_data = [
                ['Company:', budget.company],
                ['Fiscal Year:', budget.fiscal_year],
                ['Budget Type:', budget.budget_type],
                ['Budget Category:', budget.budget_category],
                ['Status:', budget.budget_status],
                ['Currency:', budget.currency],
                ['Created By:', budget.owner],
                ['Created On:', budget.creation.strftime('%Y-%m-%d') if budget.creation else '']
            ]
            
            for label, value in info_data:
                ws_summary[f'A{row}'] = label
                ws_summary[f'A{row}'].font = bold_font
                ws_summary[f'A{row}'].fill = PatternFill(start_color=colors['light'], end_color=colors['light'], fill_type='solid')
                ws_summary[f'B{row}'] = value
                ws_summary[f'B{row}'].font = normal_font
                row += 1
            
            # Total budget highlight
            row += 1
            ws_summary.merge_cells(f'A{row}:B{row}')
            cell = ws_summary[f'A{row}']
            cell.value = '💰 Total Budget'
            cell.font = Font(name='Calibri', size=14, bold=True, color=colors['white'])
            cell.fill = PatternFill(start_color=colors['success'], end_color=colors['success'], fill_type='solid')
            cell.alignment = center_align
            
            row += 1
            ws_summary.merge_cells(f'A{row}:B{row}')
            cell = ws_summary[f'A{row}']
            cell.value = flt(budget.total_budget_amount)
            cell.font = Font(name='Calibri', size=16, bold=True, color=colors['success'])
            cell.number_format = currency_format
            cell.alignment = center_align
            
            # Monthly breakdown
            row += 2
            ws_summary[f'A{row}'] = '📅 Monthly Breakdown'
            ws_summary[f'A{row}'].font = Font(name='Calibri', size=12, bold=True, color=colors['primary'])
            
            row += 1
            # Headers
            ws_summary[f'A{row}'] = 'Month'
            ws_summary[f'B{row}'] = 'Budget Amount'
            ws_summary[f'C{row}'] = '% of Total'
            
            for col in ['A', 'B', 'C']:
                ws_summary[f'{col}{row}'].fill = header_fill
                ws_summary[f'{col}{row}'].font = header_font
                ws_summary[f'{col}{row}'].alignment = center_align
                ws_summary[f'{col}{row}'].border = thin_border
            
            # Monthly data
            months = {
                'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April',
                'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August',
                'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'
            }
            
            monthly_totals = {}
            for month_key in months.keys():
                total = sum([flt(getattr(line, month_key, 0)) for line in budget.monthly_budget])
                monthly_totals[month_key] = total
            
            row += 1
            start_data_row = row
            
            for month_key, month_name in months.items():
                amount = monthly_totals.get(month_key, 0)
                percentage = (amount / flt(budget.total_budget_amount) * 100) if flt(budget.total_budget_amount) > 0 else 0
                
                ws_summary[f'A{row}'] = month_name
                ws_summary[f'B{row}'] = amount
                ws_summary[f'C{row}'] = percentage / 100
                
                ws_summary[f'A{row}'].font = normal_font
                ws_summary[f'B{row}'].font = normal_font
                ws_summary[f'C{row}'].font = normal_font
                
                ws_summary[f'A{row}'].alignment = left_align
                ws_summary[f'B{row}'].alignment = right_align
                ws_summary[f'C{row}'].alignment = right_align
                
                ws_summary[f'B{row}'].number_format = currency_format
                ws_summary[f'C{row}'].number_format = percent_format
                
                # Alternate row colors
                if row % 2 == 0:
                    for col in ['A', 'B', 'C']:
                        ws_summary[f'{col}{row}'].fill = PatternFill(start_color=colors['light'], end_color=colors['light'], fill_type='solid')
                
                for col in ['A', 'B', 'C']:
                    ws_summary[f'{col}{row}'].border = thin_border
                
                row += 1
            
            # Add chart if requested
            if int(include_charts):
                chart = BarChart()
                chart.type = "col"
                chart.style = 10
                chart.title = "Monthly Budget Distribution"
                chart.y_axis.title = 'Amount'
                chart.x_axis.title = 'Month'
                
                data = Reference(ws_summary, min_col=2, min_row=start_data_row-1, max_row=row-1)
                cats = Reference(ws_summary, min_col=1, min_row=start_data_row, max_row=row-1)
                
                chart.add_data(data, titles_from_data=True)
                chart.set_categories(cats)
                chart.height = 10
                chart.width = 20
                
                ws_summary.add_chart(chart, f'E{start_data_row}')
            
            # Adjust column widths
            ws_summary.column_dimensions['A'].width = 20
            ws_summary.column_dimensions['B'].width = 18
            ws_summary.column_dimensions['C'].width = 15
        
        # ============================================
        # DETAILED BUDGET SHEET
        # ============================================
        ws_budget = wb.create_sheet("💰 Budget Details")
        
        # Title
        ws_budget.merge_cells('A1:P1')
        cell = ws_budget['A1']
        cell.value = f"Budget Plan: {budget.name}"
        cell.font = title_font
        cell.alignment = center_align
        ws_budget.row_dimensions[1].height = 25
        
        # Subtitle
        ws_budget.merge_cells('A2:P2')
        cell = ws_budget['A2']
        cell.value = f"{budget.company} | {budget.fiscal_year} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        cell.font = Font(name='Calibri', size=10, italic=True, color='666666')
        cell.alignment = center_align
        
        # Headers
        row = 4
        headers = ['GL Account', 'Account Name', 'Cost Center', 'Jan', 'Feb', 'Mar', 'Apr', 
                  'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Total']
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws_budget.cell(row=row, column=col_idx)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border
        
        # Data rows
        row += 1
        start_data_row = row
        total_by_month = {month: 0 for month in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']}
        grand_total = 0
        
        for budget_line in budget.monthly_budget:
            col = 1
            
            # GL Account
            cell = ws_budget.cell(row=row, column=col)
            cell.value = budget_line.gl_account
            cell.font = normal_font
            cell.border = thin_border
            col += 1
            
            # Account Name
            cell = ws_budget.cell(row=row, column=col)
            cell.value = budget_line.title or ''
            cell.font = normal_font
            cell.border = thin_border
            col += 1
            
            # Cost Center
            cell = ws_budget.cell(row=row, column=col)
            cell.value = budget_line.cost_center or ''
            cell.font = normal_font
            cell.border = thin_border
            col += 1
            
            # Monthly amounts
            months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
            row_total = 0
            
            for month in months:
                amount = flt(getattr(budget_line, month, 0))
                cell = ws_budget.cell(row=row, column=col)
                cell.value = amount
                cell.number_format = currency_format
                cell.font = normal_font
                cell.alignment = right_align
                cell.border = thin_border
                
                # Color code based on amount
                if amount > 0:
                    # Green tint for positive amounts
                    intensity = min(int((amount / (flt(budget.total_budget_amount) / len(budget.monthly_budget))) * 100), 100)
                    green_value = 255 - int(intensity * 1.5)
                    color_hex = f'c8e6c9' if green_value < 200 else 'e8f5e9'
                    cell.fill = PatternFill(start_color=color_hex, end_color=color_hex, fill_type='solid')
                
                total_by_month[month] += amount
                row_total += amount
                col += 1
            
            # Row total
            cell = ws_budget.cell(row=row, column=col)
            cell.value = row_total
            cell.number_format = currency_format
            cell.font = bold_font
            cell.alignment = right_align
            cell.border = thin_border
            cell.fill = PatternFill(start_color='fff3cd', end_color='fff3cd', fill_type='solid')
            
            grand_total += row_total
            
            # Alternate row colors for readability
            if row % 2 == 0:
                for c in range(1, 4):  # First 3 columns
                    ws_budget.cell(row=row, column=c).fill = PatternFill(start_color=colors['light'], end_color=colors['light'], fill_type='solid')
            
            row += 1
        
        # Totals row
        ws_budget.cell(row=row, column=1).value = "TOTAL"
        ws_budget.cell(row=row, column=1).font = Font(name='Calibri', size=11, bold=True, color=colors['white'])
        ws_budget.cell(row=row, column=1).fill = PatternFill(start_color=colors['success'], end_color=colors['success'], fill_type='solid')
        ws_budget.cell(row=row, column=1).alignment = center_align
        
        ws_budget.merge_cells(f'A{row}:C{row}')
        
        col = 4
        for month in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']:
            cell = ws_budget.cell(row=row, column=col)
            cell.value = total_by_month[month]
            cell.number_format = currency_format
            cell.font = Font(name='Calibri', size=10, bold=True, color=colors['white'])
            cell.fill = PatternFill(start_color=colors['success'], end_color=colors['success'], fill_type='solid')
            cell.alignment = right_align
            cell.border = thin_border
            col += 1
        
        # Grand total
        cell = ws_budget.cell(row=row, column=col)
        cell.value = grand_total
        cell.number_format = currency_format
        cell.font = Font(name='Calibri', size=11, bold=True, color=colors['white'])
        cell.fill = PatternFill(start_color=colors['primary'], end_color=colors['primary'], fill_type='solid')
        cell.alignment = right_align
        cell.border = thin_border
        
        # Add chart if requested
        if int(include_charts):
            chart = LineChart()
            chart.title = "Monthly Budget Trend"
            chart.style = 12
            chart.y_axis.title = 'Amount'
            chart.x_axis.title = 'Month'
            
            data = Reference(ws_budget, min_col=4, min_row=start_data_row-1, max_col=15, max_row=row)
            chart.add_data(data, titles_from_data=True)
            
            chart.height = 10
            chart.width = 20
            
            ws_budget.add_chart(chart, f'A{row + 3}')
        
        # Adjust column widths
        ws_budget.column_dimensions['A'].width = 18
        ws_budget.column_dimensions['B'].width = 30
        ws_budget.column_dimensions['C'].width = 25
        for col in ['D','E','F','G','H','I','J','K','L','M','N','O']:
            ws_budget.column_dimensions[col].width = 12
        ws_budget.column_dimensions['P'].width = 14
        
        # ============================================
        # SCENARIOS SHEET (if applicable)
        # ============================================
        if export_type == "With Scenarios" and budget.scenario_budgets and len(budget.scenario_budgets) > 0:
            ws_scenarios = wb.create_sheet("🎯 Scenarios")
            
            # Title
            ws_scenarios.merge_cells('A1:O1')
            cell = ws_scenarios['A1']
            cell.value = "Budget Scenarios Analysis"
            cell.font = title_font
            cell.alignment = center_align
            ws_scenarios.row_dimensions[1].height = 25
            
            row = 3
            # Headers
            headers = ['Scenario', 'Type', 'Adjustment %', 'Jan', 'Feb', 'Mar', 'Apr', 
                      'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Total']
            
            for col_idx, header in enumerate(headers, 1):
                cell = ws_scenarios.cell(row=row, column=col_idx)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center_align
                cell.border = thin_border
            
            row += 1
            
            scenario_colors = {
                'Best Case': 'c8e6c9',
                'Most Likely': 'bbdefb',
                'Worst Case': 'ffcdd2'
            }
            
            for scenario in budget.scenario_budgets:
                ws_scenarios.cell(row=row, column=1).value = scenario.scenario_name
                ws_scenarios.cell(row=row, column=2).value = scenario.scenario_type
                ws_scenarios.cell(row=row, column=3).value = flt(scenario.adjustment_percentage) / 100
                ws_scenarios.cell(row=row, column=3).number_format = percent_format
                
                col = 4
                scenario_total = 0
                months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
                
                for month in months:
                    amount = flt(getattr(scenario, month, 0))
                    ws_scenarios.cell(row=row, column=col).value = amount
                    ws_scenarios.cell(row=row, column=col).number_format = currency_format
                    ws_scenarios.cell(row=row, column=col).alignment = right_align
                    scenario_total += amount
                    col += 1
                
                ws_scenarios.cell(row=row, column=col).value = scenario_total
                ws_scenarios.cell(row=row, column=col).number_format = currency_format
                ws_scenarios.cell(row=row, column=col).font = bold_font
                
                # Apply scenario color
                fill_color = scenario_colors.get(scenario.scenario_type, colors['light'])
                for c in range(1, col + 1):
                    ws_scenarios.cell(row=row, column=c).fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                    ws_scenarios.cell(row=row, column=c).border = thin_border
                
                row += 1
            
            # Adjust widths
            ws_scenarios.column_dimensions['A'].width = 25
            ws_scenarios.column_dimensions['B'].width = 15
            ws_scenarios.column_dimensions['C'].width = 15
            for col in ['D','E','F','G','H','I','J','K','L','M','N','O']:
                ws_scenarios.column_dimensions[col].width = 12
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Prepare response
        filename = f"Budget_{budget.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        frappe.response["filename"] = filename
        frappe.response["filecontent"] = output.getvalue()
        frappe.response["type"] = "binary"
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Excel Export Error")
        frappe.throw(_("Export failed: {0}").format(str(e)))