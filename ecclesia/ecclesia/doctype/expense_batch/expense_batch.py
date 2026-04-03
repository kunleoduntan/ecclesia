# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

# ============================================
# EXPENSE BATCH - ENHANCED SERVER SCRIPT
# Python code for expense_batch.py
# ============================================

import frappe
from frappe import _
from frappe.utils import flt, today, getdate, get_datetime
from frappe.model.document import Document
import json
from datetime import datetime, timedelta

class ExpenseBatch(Document):
    def validate(self):
        """Enhanced validation with AI-powered checks"""
        self.validate_dates()
        self.validate_transactions()
        self.calculate_totals()
        self.detect_anomalies()
        self.set_title()
    
    def before_submit(self):
        """Pre-submission checks"""
        self.validate_reference_and_amount()
        
        if self.post_batch:
            self.create_payment_vouchers()
    
    def validate_dates(self):
        """Validate date range"""
        if self.batch_end_date < self.batch_start_date:
            frappe.throw(_("End date cannot be before start date"))
        
        # Warn if date range is too long
        days_diff = (getdate(self.batch_end_date) - getdate(self.batch_start_date)).days
        if days_diff > 31:
            frappe.msgprint(
                _("⚠️ Batch covers more than 31 days. Consider splitting into multiple batches."),
                indicator='orange',
                alert=True
            )
    
    def validate_transactions(self):
        """Enhanced transaction validation"""
        if not self.petty_cash_transaction:
            frappe.throw(_("At least one transaction is required"))
        
        errors = []
        warnings = []
        
        for idx, row in enumerate(self.petty_cash_transaction, start=1):
            # Required fields
            if not row.date:
                errors.append(_("Row {0}: Date is required").format(idx))
            
            if not row.beneficiary:
                errors.append(_("Row {0}: Beneficiary is required").format(idx))
            
            if not row.transaction_description:
                errors.append(_("Row {0}: Transaction description is required").format(idx))
            
            if not row.account:
                errors.append(_("Row {0}: Account is required").format(idx))
            
            # Amount validation
            if flt(row.inflow) == 0 and flt(row.outflow) == 0:
                errors.append(_("Row {0}: Either inflow or outflow must be specified").format(idx))
            
            if flt(row.inflow) > 0 and flt(row.outflow) > 0:
                warnings.append(_("Row {0}: Both inflow and outflow specified. Verify if correct.").format(idx))
            
            # Date validation
            if row.date:
                if getdate(row.date) < getdate(self.batch_start_date) or getdate(row.date) > getdate(self.batch_end_date):
                    warnings.append(_("Row {0}: Transaction date outside batch date range").format(idx))
        
        if errors:
            frappe.throw("<br>".join(errors))
        
        if warnings:
            frappe.msgprint("<br>".join(warnings), indicator='orange', alert=True)
    
    def calculate_totals(self):
        """Calculate all totals and running balances"""
        total_inflow = 0
        total_outflow = 0
        running_balance = flt(self.opening_balance)
        
        for row in self.petty_cash_transaction:
            total_inflow += flt(row.inflow)
            total_outflow += flt(row.outflow)
            running_balance += flt(row.inflow) - flt(row.outflow)
            row.balance = running_balance
        
        self.total_inflow = total_inflow
        self.total_outflow = total_outflow
        self.balance = running_balance
        
        # Warn if balance is negative
        if self.balance < 0:
            frappe.msgprint(
                _("⚠️ Closing balance is negative: {0}").format(self.balance),
                indicator='red',
                alert=True
            )
    
    def detect_anomalies(self):
        """AI-powered anomaly detection"""
        anomalies = []
        
        if not self.petty_cash_transaction:
            return
        
        # Calculate statistics
        outflows = [flt(t.outflow) for t in self.petty_cash_transaction if flt(t.outflow) > 0]
        
        if outflows:
            avg_outflow = sum(outflows) / len(outflows)
            max_outflow = max(outflows)
            
            # Detect unusually large transactions
            for idx, row in enumerate(self.petty_cash_transaction, start=1):
                if flt(row.outflow) > avg_outflow * 3:
                    anomalies.append({
                        'row': idx,
                        'type': 'Large Transaction',
                        'severity': 'high',
                        'message': _("Row {0}: Amount {1} is 3x larger than average").format(idx, row.outflow)
                    })
                
                # Check for weekend transactions
                if row.date:
                    day_of_week = getdate(row.date).weekday()
                    if day_of_week >= 5:  # Saturday or Sunday
                        anomalies.append({
                            'row': idx,
                            'type': 'Weekend Transaction',
                            'severity': 'low',
                            'message': _("Row {0}: Weekend transaction detected").format(idx)
                        })
                
                # Check for round numbers
                if flt(row.outflow) > 0 and flt(row.outflow) % 1000 == 0:
                    anomalies.append({
                        'row': idx,
                        'type': 'Round Number',
                        'severity': 'low',
                        'message': _("Row {0}: Round number amount - verify if actual").format(idx)
                    })
        
        # Check for duplicate beneficiaries on same date
        date_beneficiary_map = {}
        for idx, row in enumerate(self.petty_cash_transaction, start=1):
            key = f"{row.date}_{row.beneficiary}"
            if key in date_beneficiary_map:
                anomalies.append({
                    'row': idx,
                    'type': 'Potential Duplicate',
                    'severity': 'medium',
                    'message': _("Row {0}: Duplicate beneficiary on same date (also in row {1})").format(
                        idx, date_beneficiary_map[key])
                })
            else:
                date_beneficiary_map[key] = idx
        
        if anomalies:
            self.log_anomalies(anomalies)
    
    def log_anomalies(self, anomalies):
        """Log detected anomalies"""
        # You can store this in a custom field or create a separate log
        high_severity = [a for a in anomalies if a['severity'] == 'high']
        
        if high_severity:
            message = _("🚨 {0} high-severity anomalies detected:<br>").format(len(high_severity))
            for anomaly in high_severity[:5]:  # Show first 5
                message += f"• {anomaly['message']}<br>"
            
            frappe.msgprint(message, indicator='red', alert=True)
    
    def validate_reference_and_amount(self):
        """Check for duplicate payments"""
        for row in self.petty_cash_transaction:
            if flt(row.outflow) > 0:
                reference_no = row.name[-7:].upper()
                
                # Check if payment already exists
                existing = frappe.db.exists("Payments", {
                    "reference_no": reference_no,
                    "amount_paid": row.outflow
                })
                
                if existing:
                    frappe.throw(
                        _("The reference number {0} with amount {1} already exists in Payments. Batch may be already posted.").format(
                            reference_no, row.outflow
                        )
                    )
    
    def create_payment_vouchers(self):
        """Create payment vouchers with enhanced error handling"""
        if not self.post_batch:
            return
        
        created_payments = []
        failed_payments = []
        
        for row in self.petty_cash_transaction:
            if flt(row.outflow) > 0:
                try:
                    payment = self.create_single_payment(row)
                    created_payments.append(payment.name)
                except Exception as e:
                    failed_payments.append({
                        'row': row.idx,
                        'error': str(e)
                    })
                    frappe.log_error(
                        title=f"Payment Creation Failed - {row.name}",
                        message=frappe.get_traceback()
                    )
        
        # Show summary
        if created_payments:
            frappe.msgprint(
                _("✅ Successfully created {0} payment voucher(s)").format(len(created_payments)),
                indicator='green',
                alert=True
            )
        
        if failed_payments:
            error_msg = _("❌ Failed to create {0} payment(s):<br>").format(len(failed_payments))
            for fail in failed_payments[:5]:  # Show first 5
                error_msg += f"• Row {fail['row']}: {fail['error']}<br>"
            
            frappe.msgprint(error_msg, indicator='red', alert=True)
    
    def create_single_payment(self, row):
        """Create a single payment voucher"""
        payment = frappe.new_doc('Payments')
        
        # Basic details
        payment.transaction_date = row.date
        payment.payee_name = (row.beneficiary or "").title()
        payment.account_to_debit = row.account
        payment.trans_type = "Expense Payment"
        payment.payment_currency = self.account_currency or "NGN"
        payment.cost_center = self.cost_center
        
        # Transaction details
        payment.transaction_purposes = (row.transaction_description or "").title()
        payment.mode_of_payment = "Cash"
        payment.remittance_bank = self.petty_cash_account
        payment.amount_paid = row.outflow
        
        # Exchange rate
        if self.account_currency == "NGN":
            payment.exchange_rate = 1
        else:
            payment.exchange_rate = self.get_exchange_rate()
        
        # Additional fields
        payment.nature_of_expense = "Internal"
        payment.create_accounting_entries = 1
        payment.approval_doc = row.name[-7:].upper()
        payment.reference_no = row.name[-7:].upper()
        payment.issued_by = self.prepared_by or frappe.session.user
        payment.date = today()
        payment.cashflow_type = "Payment of Operation"
        payment.auth_date = today()
        payment.app_date = today()
        
        # Insert and return
        payment.insert(ignore_permissions=True)
        return payment
    
    def get_exchange_rate(self):
        """Get current exchange rate for currency"""
        if self.account_currency == "NGN":
            return 1
        
        # Fetch latest exchange rate
        exchange_rate = frappe.db.get_value(
            "Currency Exchange",
            {
                "from_currency": self.account_currency,
                "to_currency": frappe.defaults.get_global_default("currency")
            },
            "exchange_rate"
        )
        
        return flt(exchange_rate) if exchange_rate else 1
    
    def set_title(self):
        """Set document title"""
        if self.cost_center and self.employee_name:
            self.title = f"{self.cost_center} - {self.employee_name}"
        elif self.cost_center:
            self.title = self.cost_center
        else:
            self.title = f"Batch {self.name}"


# ============================================
# API METHODS
# ============================================

@frappe.whitelist()
def analyze_expense_batch(doc):
    """AI-powered expense analysis"""
    if isinstance(doc, str):
        doc = json.loads(doc)
    
    analysis = {
        'summary': '',
        'recommendations': [],
        'risks': [],
        'insights': {}
    }
    
    # Calculate metrics
    total_outflow = flt(doc.get('total_outflow', 0))
    opening_balance = flt(doc.get('opening_balance', 0))
    transactions = doc.get('petty_cash_transaction', [])
    
    if not transactions:
        return analysis
    
    # Budget utilization
    budget_used = (total_outflow / opening_balance * 100) if opening_balance > 0 else 0
    analysis['insights']['budget_utilization'] = f"{budget_used:.1f}%"
    
    # Spending patterns
    outflows = [flt(t.get('outflow', 0)) for t in transactions if flt(t.get('outflow', 0)) > 0]
    if outflows:
        avg_transaction = sum(outflows) / len(outflows)
        max_transaction = max(outflows)
        
        analysis['summary'] = f"Analyzed {len(transactions)} transactions. Average transaction: {avg_transaction:.2f}"
        
        # Recommendations
        if budget_used > 80:
            analysis['recommendations'].append("Budget utilization is high (>80%). Consider requesting additional funds.")
        
        if max_transaction > avg_transaction * 3:
            analysis['recommendations'].append("Some transactions are significantly larger than average. Review for accuracy.")
        
        # Count weekend transactions
        weekend_count = sum(1 for t in transactions 
                          if t.get('date') and getdate(t['date']).weekday() >= 5)
        if weekend_count > 0:
            analysis['risks'].append(f"{weekend_count} weekend transaction(s) detected. Verify if legitimate.")
        
        # Check for missing documentation
        missing_desc = sum(1 for t in transactions if not t.get('transaction_description'))
        if missing_desc > 0:
            analysis['risks'].append(f"{missing_desc} transaction(s) missing descriptions.")
    
    return analysis


@frappe.whitelist()
def check_duplicate_payments(doc):
    """Check for duplicate payments"""
    if isinstance(doc, str):
        doc = json.loads(doc)
    
    duplicates = []
    transactions = doc.get('petty_cash_transaction', [])
    
    for row in transactions:
        if flt(row.get('outflow', 0)) > 0:
            reference_no = row.get('name', '')[-7:].upper()
            
            existing = frappe.db.get_all(
                "Payments",
                filters={
                    "reference_no": reference_no,
                    "amount_paid": row.get('outflow')
                },
                fields=['name', 'transaction_date', 'payee_name']
            )
            
            if existing:
                duplicates.extend(existing)
    
    return duplicates


@frappe.whitelist()
def get_expense_analytics(cost_center=None, from_date=None, to_date=None):
    """Get expense analytics for dashboard"""
    filters = {}
    
    if cost_center:
        filters['cost_center'] = cost_center
    
    if from_date and to_date:
        filters['batch_start_date'] = ['between', [from_date, to_date]]
    
    batches = frappe.get_all(
        'Expense Batch',
        filters=filters,
        fields=['name', 'total_inflow', 'total_outflow', 'balance', 'batch_start_date']
    )
    
    analytics = {
        'total_batches': len(batches),
        'total_spent': sum(b['total_outflow'] for b in batches),
        'total_received': sum(b['total_inflow'] for b in batches),
        'average_batch_size': sum(b['total_outflow'] for b in batches) / len(batches) if batches else 0
    }
    
    return analytics


@frappe.whitelist()
def auto_categorize_transaction(description):
    """Auto-categorize expense based on description"""
    categories = {
        'Transport': ['taxi', 'uber', 'fuel', 'transport', 'bus', 'logistics', 'vehicle'],
        'Meals': ['lunch', 'dinner', 'breakfast', 'food', 'restaurant', 'meal', 'catering'],
        'Supplies': ['stationery', 'supplies', 'office', 'paper', 'pen', 'material'],
        'Utilities': ['electricity', 'water', 'internet', 'phone', 'utility', 'telecom'],
        'Maintenance': ['repair', 'maintenance', 'fix', 'service', 'cleaning'],
        'Professional': ['consultant', 'legal', 'audit', 'professional', 'advisory'],
        'Travel': ['hotel', 'accommodation', 'flight', 'travel', 'lodging'],
        'Medical': ['medical', 'health', 'clinic', 'hospital', 'medicine']
    }
    
    description_lower = description.lower()
    
    for category, keywords in categories.items():
        if any(keyword in description_lower for keyword in keywords):
            return category
    
    return 'Other'


# ============================================
# SCHEDULED TASKS
# ============================================

def send_batch_reminders():
    """Send reminders for pending expense batches (scheduled daily)"""
    pending_batches = frappe.get_all(
        'Expense Batch',
        filters={
            'docstatus': 0,
            'creation': ['<', get_datetime() - timedelta(days=3)]
        },
        fields=['name', 'prepared_by', 'cost_center']
    )
    
    for batch in pending_batches:
        try:
            # Send email reminder
            frappe.sendmail(
                recipients=[batch.prepared_by],
                subject=_("Reminder: Pending Expense Batch {0}").format(batch.name),
                message=_("""
                    <p>Dear User,</p>
                    <p>Your expense batch <strong>{0}</strong> for <strong>{1}</strong> 
                    has been pending for more than 3 days.</p>
                    <p>Please review and submit it at your earliest convenience.</p>
                    <p><a href="{2}/app/expense-batch/{3}">View Batch</a></p>
                """).format(batch.name, batch.cost_center, frappe.utils.get_url(), batch.name)
            )
        except Exception as e:
            frappe.log_error(
                title=f"Batch Reminder Failed - {batch.name}",
                message=frappe.get_traceback()
            )


def generate_expense_report():
    """Generate monthly expense report (scheduled monthly)"""
    try:
        # Get current month batches
        from_date = get_datetime().replace(day=1)
        to_date = get_datetime()
        
        batches = frappe.get_all(
            'Expense Batch',
            filters={
                'batch_start_date': ['between', [from_date, to_date]],
                'docstatus': 1
            },
            fields=['cost_center', 'total_outflow', 'total_inflow']
        )
        
        # Group by cost center
        report_data = {}
        for batch in batches:
            cc = batch.cost_center
            if cc not in report_data:
                report_data[cc] = {'outflow': 0, 'inflow': 0}
            
            report_data[cc]['outflow'] += flt(batch.total_outflow)
            report_data[cc]['inflow'] += flt(batch.total_inflow)
        
        # Send report to finance team
        # Implementation depends on your requirements
        return report_data
        
    except Exception as e:
        frappe.log_error(
            title="Monthly Expense Report Generation Failed",
            message=frappe.get_traceback()
        )
        return {}