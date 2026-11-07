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
from ecclesia.api import voucher_router as vr
from ecclesia.api import batch_excel_io as xio


# Excel layout (Petty Cash Transaction child table).  Order is cosmetic: import
# matches columns by header name.
_SHEET = "Expenses"
_COLUMNS = [
    ("Date*",         "date",                    True,  "date",  {"width": 12, "example": "2026-11-02"}),
    ("Beneficiary*",  "beneficiary",             True,  "str",   {"width": 26, "example": "Ade Stores"}),
    ("Description*",  "transaction_description", True,  "str",   {"width": 40, "example": "Office stationery"}),
    ("Account*",      "account",                 True,  "str",   {"width": 30, "link": "Account",
                                                                   "note": "Expense GL account (not a group).",
                                                                   "example": "Printing and Stationery - VIC"}),
    ("Inflow",        "inflow",                  False, "float", {"width": 14, "note": "Cash received into petty cash."}),
    ("Outflow",       "outflow",                 False, "float", {"width": 14, "note": "Cash paid out. Only outflows are posted.",
                                                                   "example": 15000}),
    ("Cost Center",   "cost_center",             False, "str",   {"width": 24, "link": "Cost Center",
                                                                   "note": "Blank = the batch cost center."}),
]
_STATUS_COLUMNS = [
    ("Balance", "balance", 14), ("Entry Created", "_created", 14),
    ("Entry Type", "entry_type_created", 16), ("Entry Reference", "entry_reference", 22),
]


class ExpenseBatch(Document):
    def validate(self):
        """Enhanced validation with AI-powered checks"""
        self.set_default_policy()
        self.validate_dates()
        self.validate_transactions()
        self.calculate_totals()
        self.detect_anomalies()
        self.set_title()

    def set_default_policy(self):
        # Records saved before the field existed keep their original behaviour
        # (Payments vouchers).
        self.posting_policy = vr.resolve_policy(self.get("posting_policy"), default=vr.POLICY_VOUCHERS)

    def before_submit(self):
        """Pre-submission checks"""
        self.validate_reference_and_amount()

    def on_submit(self):
        if self.post_batch:
            self.create_payment_vouchers()

    def on_cancel(self):
        self.cancel_posted_entries()

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
        """Guard against posting the same batch twice."""
        policy = self.posting_policy
        for row in self.petty_cash_transaction:
            if flt(row.outflow) <= 0 or row.get("entry_reference"):
                continue
            reference_no = row.name[-7:].upper()
            if policy == vr.POLICY_VOUCHERS:
                existing = frappe.db.exists("Payments", {
                    "reference_no": reference_no, "amount_paid": row.outflow, "docstatus": ["<", 2]})
            else:
                existing = frappe.db.exists("Journal Entry", {
                    "cheque_no": reference_no, "docstatus": ["<", 2]})
            if existing:
                frappe.throw(_("Reference {0} with amount {1} already exists ({2}). "
                               "Batch may be already posted.").format(reference_no, row.outflow, existing))

    def _line(self, row):
        """Petty cash outflow -> router line (Dr expense account, Cr petty cash)."""
        return {
            "idx": row.idx,
            "trans_type": "Payment",
            "posting_date": row.date,
            "amount": flt(row.outflow),
            "remark": (row.transaction_description or "").title(),
            "payee_name": (row.beneficiary or "").title(),
            "counter_account": row.account,
            "bank_account_gl": self.petty_cash_account,
            "mode_of_payment": "Cash",
            "reference_no": row.name[-7:].upper(),
            "cost_center": row.cost_center or self.cost_center,
            "nature_of_expense": "Internal",
            "issued_by": self.prepared_by or frappe.session.user,
            "cashflow_type": "Operating costs",
        }

    def create_payment_vouchers(self):
        """
        Post every outflow row using the batch's Posting Policy.
        Inflows are NOT posted (they are the cash top-up that funds the batch).
        All-or-nothing: any failure aborts the submit and rolls everything back,
        so a batch can never be half posted.
        """
        policy = self.posting_policy
        created, errors = [], []
        for row in self.petty_cash_transaction:
            if flt(row.outflow) <= 0 or row.get("entry_reference"):
                continue
            try:
                name, dt = vr.create_entry(
                    self._line(row), policy, self.company, self.petty_cash_account,
                    source_doctype=self.doctype, source_name=self.name,
                    source_row=row.name, submit=False, default_mode="Cash")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Expense Batch {self.name}: row {row.idx}")
                errors.append(str(e) if str(e).startswith("Row ") else f"Row {row.idx}: {e}")
                continue
            frappe.db.set_value(row.doctype, row.name,
                                {"entry_type_created": dt, "entry_reference": name},
                                update_modified=False)
            created.append(name)

        if errors:
            frappe.throw("<br>".join(errors[:10]) + (f"<br>... and {len(errors) - 10} more" if len(errors) > 10 else ""),
                         title=_("Batch not posted - fix these rows"))
        if created:
            frappe.msgprint(_("{0} {1} created as Draft.").format(
                len(created), "Payments voucher(s)" if policy == vr.POLICY_VOUCHERS else "Journal Entr(ies)"),
                indicator="green", alert=True)

    def cancel_posted_entries(self):
        done = {"cancelled": 0, "deleted": 0}
        for row in self.petty_cash_transaction:
            dt, name = row.get("entry_type_created"), row.get("entry_reference")
            try:
                res = vr.cancel_or_delete(dt, name)
            except Exception:
                frappe.log_error(frappe.get_traceback(), f"Expense Batch {self.name}: cancel {dt} {name}")
                frappe.throw(_("Could not cancel {0} {1}. Cancel it manually first.").format(dt, name))
            if res:
                done[res] += 1
        if done["cancelled"] or done["deleted"]:
            frappe.msgprint(_("{0} entr(ies) cancelled, {1} draft(s) deleted.").format(
                done["cancelled"], done["deleted"]), indicator="orange", alert=True)

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

# ============================================
# EXCEL TEMPLATE / EXPORT / IMPORT
# ============================================

@frappe.whitelist()
def download_template():
    b64 = xio.build_workbook(_SHEET, _COLUMNS, template=True)
    return {"filename": "Expense_Batch_Template.xlsx", "file_content": b64}


@frappe.whitelist()
def export_to_excel(doc_name):
    doc = frappe.get_doc("Expense Batch", doc_name)
    doc.check_permission("read")
    rows = []
    for r in doc.petty_cash_transaction:
        rec = {c[1]: r.get(c[1]) for c in _COLUMNS}
        rec.update({"balance": flt(r.get("balance")),
                    "_created": "YES" if r.get("entry_reference") else "NO",
                    "entry_type_created": r.get("entry_type_created") or "",
                    "entry_reference": r.get("entry_reference") or "",
                    "_done": bool(r.get("entry_reference"))})
        rows.append(rec)
    info = [
        ("Expense Batch", doc.name), ("Company", doc.get("company") or ""),
        ("Cost Center", doc.get("cost_center") or ""),
        ("Period", f"{doc.get('batch_start_date')} to {doc.get('batch_end_date')}"),
        ("Posting Policy", doc.get("posting_policy") or ""),
        ("Opening Balance", flt(doc.get("opening_balance"))),
        ("Total Inflow", flt(doc.get("total_inflow"))), ("Total Outflow", flt(doc.get("total_outflow"))),
        ("Closing Balance", flt(doc.get("balance"))), ("Exported By", frappe.session.user),
        ("Exported At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]
    b64 = xio.build_workbook(_SHEET, _COLUMNS, rows, _STATUS_COLUMNS, info)
    return {"filename": f"ExpenseBatch_{doc.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "file_content": b64}


@frappe.whitelist()
def import_from_excel(doc_name, file_content, filename, replace_existing=0):
    doc = frappe.get_doc("Expense Batch", doc_name)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw(_("Rows can only be imported into a Draft batch."))

    records, errors, skipped = xio.parse_rows(file_content, filename, _SHEET, _COLUMNS,
                                              describe_field="transaction_description")
    good = []
    for rec in records:
        inflow, outflow = flt(rec.get("inflow")), flt(rec.get("outflow"))
        if inflow <= 0 and outflow <= 0:
            errors.append({"row": rec.get("_excel_row"), "description": rec.get("transaction_description") or "",
                           "errors": ["Either Inflow or Outflow must be greater than zero"]})
            skipped += 1
            continue
        if inflow > 0 and outflow > 0:
            errors.append({"row": rec.get("_excel_row"), "description": rec.get("transaction_description") or "",
                           "errors": ["Use Inflow OR Outflow on a row, not both"]})
            skipped += 1
            continue
        rec.pop("_excel_row", None)
        rec["inflow"], rec["outflow"] = inflow, outflow
        rec["cost_center"] = rec.get("cost_center") or doc.cost_center
        good.append(rec)

    if good:
        if int(replace_existing or 0):
            doc.set("petty_cash_transaction", [])
        for rec in good:
            doc.append("petty_cash_transaction", rec)
        doc.save()
        frappe.db.commit()
    return xio.import_result(len(good), skipped, errors)
