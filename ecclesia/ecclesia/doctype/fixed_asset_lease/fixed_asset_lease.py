# -*- coding: utf-8 -*-
# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, add_months, get_last_day, date_diff, add_days


class FixedAssetLease(Document):
    def validate(self):
        """Validate lease document"""
        self.validate_asset()
        self.validate_dates()
        self.validate_party()
        self.calculate_lease_term()
        self.calculate_totals()
        self.calculate_present_value()
        self.validate_payment_schedule()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.lease_payment_schedule:
            frappe.throw(_("Please generate payment schedule"))
        
        if not self.lease_classification:
            frappe.throw(_("Lease Classification is required"))
    
    def on_submit(self):
        """On submit operations"""
        self.update_asset_lease_status()
        self.create_lease_accounting_entries()
        self.lease_status = "Active"
        self.db_set("lease_status", "Active")
    
    def on_cancel(self):
        """On cancel operations"""
        self.revert_asset_lease_status()
        self.reverse_accounting_entries()
        self.lease_status = "Cancelled"
        self.db_set("lease_status", "Cancelled")
    
    def validate_asset(self):
        """Validate asset details"""
        if not self.asset:
            frappe.throw(_("Asset is required"))
        
        if not frappe.db.exists("Fixed Asset", self.asset):
            frappe.throw(_("Invalid Asset"))
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if asset.docstatus != 1:
            frappe.throw(_("Asset must be submitted"))
        
        # For Lease Out, asset must not be already leased
        if self.lease_type == "Lease Out (We are Lessor)":
            existing_lease = frappe.db.exists("Fixed Asset Lease", {
                "asset": self.asset,
                "docstatus": 1,
                "lease_status": ["in", ["Active", "Grace Period"]],
                "name": ["!=", self.name]
            })
            
            if existing_lease:
                frappe.throw(_("Asset is already leased out"))
        
        # Fetch asset details
        self.asset_name = asset.asset_name
        self.asset_code = asset.asset_code
        self.asset_category = asset.asset_category
        
        # Set fair value if not set
        if not self.asset_fair_value:
            self.asset_fair_value = asset.current_gross_value or asset.gross_purchase_amount
    
    def validate_dates(self):
        """Validate dates"""
        if not self.lease_start_date or not self.lease_end_date:
            frappe.throw(_("Lease Start Date and Lease End Date are required"))
        
        if getdate(self.lease_end_date) <= getdate(self.lease_start_date):
            frappe.throw(_("Lease End Date must be after Lease Start Date"))
        
        if hasattr(self, 'lease_date') and self.lease_date:
            if getdate(self.lease_start_date) < getdate(self.lease_date):
                frappe.throw(_("Lease Start Date cannot be before Lease Date"))
    
    def validate_party(self):
        """Validate party details"""
        if self.lease_type == "Lease In (We are Lessee)":
            if not self.lessor:
                frappe.throw(_("Lessor is required for Lease In"))
        elif self.lease_type == "Lease Out (We are Lessor)":
            if not self.lessee:
                frappe.throw(_("Lessee is required for Lease Out"))
    
    def calculate_lease_term(self):
        """Calculate lease term in months"""
        if self.lease_start_date and self.lease_end_date:
            start = getdate(self.lease_start_date)
            end = getdate(self.lease_end_date)
            
            # Calculate months
            months = (end.year - start.year) * 12 + (end.month - start.month)
            
            # Add 1 if there are remaining days
            if end.day >= start.day:
                months += 1
            
            self.lease_term_months = months
    
    def calculate_totals(self):
        """Calculate total lease payments"""
        if not self.lease_payment_amount or not self.lease_term_months or not self.payment_frequency:
            return
        
        freq_map = {
            "Monthly": 1,
            "Quarterly": 3,
            "Semi-Annual": 6,
            "Annual": 12
        }
        
        freq_months = freq_map.get(self.payment_frequency, 1)
        periods = int(self.lease_term_months / freq_months)
        
        self.number_of_payments = periods
        self.total_lease_payments = flt(self.lease_payment_amount) * periods
    
    def calculate_present_value(self):
        """Calculate present value of lease payments"""
        if self.lease_classification != "Finance Lease":
            return
        
        if not self.discount_rate:
            # Use implicit rate or incremental borrowing rate
            self.discount_rate = self.implicit_interest_rate or self.incremental_borrowing_rate
        
        if not self.discount_rate or not self.lease_payment_amount or not self.number_of_payments:
            return
        
        # Calculate present value
        rate = flt(self.discount_rate) / 100
        
        # Convert to period rate based on frequency
        frequency_map = {
            "Monthly": 12,
            "Quarterly": 4,
            "Semi-Annual": 2,
            "Annual": 1
        }
        
        periods_per_year = frequency_map.get(self.payment_frequency, 12)
        period_rate = rate / periods_per_year
        
        payment = flt(self.lease_payment_amount)
        n = cint(self.number_of_payments)
        
        # PV of annuity formula
        if period_rate > 0:
            pv = payment * ((1 - pow(1 + period_rate, -n)) / period_rate)
        else:
            pv = payment * n
        
        # Add residual value PV if applicable
        if self.residual_value and period_rate > 0:
            pv += flt(self.residual_value) / pow(1 + period_rate, n)
        
        self.present_value_of_lease_payments = pv
        
        # Calculate total interest
        self.total_interest_expense = flt(self.total_lease_payments) - pv
        
        # Calculate depreciation for lessee
        if self.lease_type == "Lease In (We are Lessee)":
            self.calculate_depreciation()
    
    def calculate_depreciation(self):
        """Calculate depreciation for finance lease (lessee)"""
        if self.lease_classification != "Finance Lease":
            return
        
        if self.lease_type != "Lease In (We are Lessee)":
            return
        
        # Determine useful life
        if not self.useful_life_months:
            self.useful_life_months = self.lease_term_months
        
        # Calculate monthly depreciation
        if self.depreciation_method == "Straight Line":
            depreciable_amount = flt(self.present_value_of_lease_payments) - flt(self.residual_value)
            if self.useful_life_months > 0:
                self.monthly_depreciation = depreciable_amount / flt(self.useful_life_months)
    
    def validate_payment_schedule(self):
        """Validate payment schedule"""
        if not self.lease_payment_schedule:
            return
        
        total_payments = sum(flt(d.payment_amount) for d in self.lease_payment_schedule)
        
        if flt(self.total_lease_payments) > 0:
            if abs(total_payments - flt(self.total_lease_payments)) > 0.01:
                frappe.throw(_("Sum of payment schedule ({0}) does not match Total Lease Payments ({1})").format(
                    total_payments, self.total_lease_payments))
    
    def update_asset_lease_status(self):
        """Update asset with lease information"""
        if not self.asset:
            return
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if self.lease_type == "Lease Out (We are Lessor)":
            asset.db_set("is_leased_out", 1)
            if hasattr(asset, 'lease_status'):
                asset.db_set("lease_status", "Leased Out")
        else:
            if hasattr(asset, 'is_leased_in'):
                asset.db_set("is_leased_in", 1)
            if hasattr(asset, 'lease_status'):
                asset.db_set("lease_status", "Leased In")
        
        if hasattr(asset, 'lease_contract'):
            asset.db_set("lease_contract", self.name)
    
    def revert_asset_lease_status(self):
        """Revert asset lease status"""
        if not self.asset:
            return
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if hasattr(asset, 'is_leased_out'):
            asset.db_set("is_leased_out", 0)
        if hasattr(asset, 'is_leased_in'):
            asset.db_set("is_leased_in", 0)
        if hasattr(asset, 'lease_status'):
            asset.db_set("lease_status", None)
        if hasattr(asset, 'lease_contract'):
            asset.db_set("lease_contract", None)
    
    def create_lease_accounting_entries(self):
        """Create initial accounting entries for finance lease"""
        if self.lease_classification != "Finance Lease":
            return
        
        if self.lease_type != "Lease In (We are Lessee)":
            return
        
        if not self.right_of_use_asset_account or not self.lease_liability_account:
            frappe.msgprint(_("Please set Right-of-Use Asset and Lease Liability accounts"))
            return
        
        if not self.present_value_of_lease_payments:
            frappe.msgprint(_("Present Value of Lease Payments not calculated"))
            return
        
        # Create Journal Entry for initial recognition
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = self.lease_start_date
        je.company = self.company
        je.user_remark = f"Finance Lease Initial Recognition - {self.asset_name}"
        
        # Debit: Right-of-Use Asset
        je.append("accounts", {
            "account": self.right_of_use_asset_account,
            "debit_in_account_currency": flt(self.present_value_of_lease_payments),
            "reference_type": "Fixed Asset Lease",
            "reference_name": self.name,
            "cost_center": self.cost_center
        })
        
        # Credit: Lease Liability
        je.append("accounts", {
            "account": self.lease_liability_account,
            "credit_in_account_currency": flt(self.present_value_of_lease_payments),
            "reference_type": "Fixed Asset Lease",
            "reference_name": self.name,
            "cost_center": self.cost_center
        })
        
        try:
            je.flags.ignore_permissions = True
            je.insert()
            je.submit()
            
            self.db_set("journal_entry", je.name)
            
            frappe.msgprint(_("Initial lease accounting entry created: {0}").format(
                frappe.utils.get_link_to_form("Journal Entry", je.name)))
        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Lease Journal Entry Creation Failed: {self.name}"
            )
            frappe.msgprint(_("Warning: Failed to create journal entry: {0}").format(str(e)), indicator="orange")
    
    def reverse_accounting_entries(self):
        """Reverse accounting entries on cancellation"""
        # Find and cancel journal entry
        if self.journal_entry:
            try:
                je = frappe.get_doc("Journal Entry", self.journal_entry)
                if je.docstatus == 1:
                    je.flags.ignore_permissions = True
                    je.cancel()
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Lease JE Cancellation Failed: {self.journal_entry}"
                )
        
        # Find and cancel all related journal entries
        journal_entries = frappe.get_all("Journal Entry Account",
            filters={
                "reference_type": "Fixed Asset Lease",
                "reference_name": self.name
            },
            fields=["parent"],
            distinct=True
        )
        
        for je_account in journal_entries:
            try:
                je = frappe.get_doc("Journal Entry", je_account.parent)
                if je.docstatus == 1:
                    je.flags.ignore_permissions = True
                    je.cancel()
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Lease JE Cancellation Failed: {je_account.parent}"
                )


# Whitelisted methods

@frappe.whitelist()
def get_asset_details(asset):
    """Get asset details for lease form"""
    if not asset:
        return {}
    
    asset_doc = frappe.get_doc("Fixed Asset", asset)
    
    return {
        "asset_code": asset_doc.asset_code,
        "asset_name": asset_doc.asset_name,
        "asset_category": asset_doc.asset_category,
        "cost_center": asset_doc.cost_center,
        "current_value": asset_doc.current_gross_value or asset_doc.gross_purchase_amount
    }


@frappe.whitelist()
def calculate_lease_values(doc):
    """Calculate lease values (PV, interest, etc.)"""
    import json
    if isinstance(doc, str):
        doc = json.loads(doc)
    
    doc = frappe._dict(doc)
    
    if not doc.lease_payment_amount or not doc.number_of_payments or not doc.discount_rate:
        frappe.throw(_("Payment Amount, Number of Payments, and Discount Rate are required"))
    
    # Calculate present value
    rate = flt(doc.discount_rate) / 100
    
    frequency_map = {
        "Monthly": 12,
        "Quarterly": 4,
        "Semi-Annual": 2,
        "Annual": 1
    }
    
    periods_per_year = frequency_map.get(doc.payment_frequency, 12)
    period_rate = rate / periods_per_year
    
    payment = flt(doc.lease_payment_amount)
    n = cint(doc.number_of_payments)
    
    # PV calculation
    if period_rate > 0:
        pv = payment * ((1 - pow(1 + period_rate, -n)) / period_rate)
    else:
        pv = payment * n
    
    # Add residual value PV
    if doc.residual_value and period_rate > 0:
        pv += flt(doc.residual_value) / pow(1 + period_rate, n)
    
    total_payments = payment * n
    total_interest = total_payments - pv
    
    return {
        "present_value": pv,
        "total_interest": total_interest
    }


@frappe.whitelist()
def generate_payment_schedule(doc):
    """Generate lease payment schedule"""
    import json
    if isinstance(doc, str):
        doc = json.loads(doc)
    
    doc = frappe._dict(doc)
    
    if not doc.lease_start_date or not doc.lease_term_months or not doc.lease_payment_amount:
        frappe.throw(_("Lease Start Date, Lease Term, and Payment Amount are required"))
    
    frequency_map = {
        "Monthly": 1,
        "Quarterly": 3,
        "Semi-Annual": 6,
        "Annual": 12
    }
    
    frequency_months = frequency_map.get(doc.payment_frequency, 1)
    number_of_payments = int(cint(doc.lease_term_months) / frequency_months)
    
    schedule = []
    outstanding_liability = flt(doc.present_value_of_lease_payments or 0)
    
    # Calculate period rate
    discount_rate = flt(doc.discount_rate) / 100 if doc.discount_rate else 0
    periods_per_year = 12 / frequency_months
    period_rate = discount_rate / periods_per_year if discount_rate > 0 else 0
    
    payment_date = getdate(doc.lease_start_date)
    
    for i in range(1, number_of_payments + 1):
        # Calculate payment date
        payment_date = add_months(getdate(doc.lease_start_date), frequency_months * i)
        
        # For finance lease, calculate principal and interest
        if doc.lease_classification == "Finance Lease" and period_rate > 0 and outstanding_liability > 0:
            interest_component = outstanding_liability * period_rate
            principal_component = flt(doc.lease_payment_amount) - interest_component
            outstanding_liability -= principal_component
            
            # Ensure outstanding doesn't go negative
            if outstanding_liability < 0:
                principal_component += outstanding_liability
                outstanding_liability = 0
        else:
            principal_component = 0
            interest_component = 0
        
        schedule.append({
            "payment_number": i,
            "payment_date": payment_date,
            "payment_amount": flt(doc.lease_payment_amount),
            "principal_amount": principal_component,
            "interest_amount": interest_component,
            "outstanding_balance": max(outstanding_liability, 0),
            "payment_status": "Pending"
        })
    
    return schedule


@frappe.whitelist()
def create_initial_journal_entry(lease_doc):
    """Create initial journal entry for finance lease"""
    lease = frappe.get_doc("Fixed Asset Lease", lease_doc)
    
    if lease.lease_classification != "Finance Lease":
        frappe.throw(_("Initial JE is only for Finance Leases"))
    
    if lease.journal_entry:
        frappe.throw(_("Initial journal entry already created"))
    
    lease.create_lease_accounting_entries()
    
    return frappe.get_doc("Journal Entry", lease.journal_entry) if lease.journal_entry else None


@frappe.whitelist()
def record_lease_payment(lease_doc, payment_details):
    """Record lease payment"""
    import json
    if isinstance(payment_details, str):
        payment_details = json.loads(payment_details)
    
    lease = frappe.get_doc("Fixed Asset Lease", lease_doc)
    
    # Find next pending payment
    next_payment = None
    for payment in lease.lease_payment_schedule:
        if payment.payment_status == "Pending":
            next_payment = payment
            break
    
    if not next_payment:
        frappe.throw(_("No pending payments found"))
    
    # Create payment entry based on lease classification
    if lease.lease_classification == "Operating Lease":
        create_operating_lease_entry(lease, next_payment, payment_details)
    else:
        create_finance_lease_payment_entry(lease, next_payment, payment_details)
    
    # Update payment status
    next_payment.payment_status = "Paid"
    next_payment.actual_payment_date = payment_details.get("payment_date")
    next_payment.payment_reference = payment_details.get("payment_reference")
    
    lease.save()
    
    return True


def create_operating_lease_entry(lease, schedule, payment_details):
    """Create journal entry for operating lease payment"""
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = payment_details.get("payment_date") or schedule.payment_date
    je.company = lease.company
    je.user_remark = f"Operating Lease Payment #{schedule.payment_number} - {lease.asset_name}"
    
    # Debit: Lease Expense
    expense_account = lease.lease_expense_account or frappe.db.get_value("Company", lease.company, "default_expense_account")
    
    je.append("accounts", {
        "account": expense_account,
        "debit_in_account_currency": flt(schedule.payment_amount),
        "reference_type": "Fixed Asset Lease",
        "reference_name": lease.name,
        "cost_center": lease.cost_center
    })
    
    # Credit: Cash/Bank
    default_cash_account = frappe.db.get_value("Company", lease.company, "default_cash_account")
    
    je.append("accounts", {
        "account": default_cash_account,
        "credit_in_account_currency": flt(schedule.payment_amount),
        "reference_type": "Fixed Asset Lease",
        "reference_name": lease.name,
        "cost_center": lease.cost_center
    })
    
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    
    schedule.journal_entry = je.name


def create_finance_lease_payment_entry(lease, schedule, payment_details):
    """Create journal entry for finance lease payment"""
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = payment_details.get("payment_date") or schedule.payment_date
    je.company = lease.company
    je.user_remark = f"Finance Lease Payment #{schedule.payment_number} - {lease.asset_name}"
    
    # Debit: Lease Liability (principal)
    if flt(schedule.principal_amount) > 0:
        je.append("accounts", {
            "account": lease.lease_liability_account,
            "debit_in_account_currency": flt(schedule.principal_amount),
            "reference_type": "Fixed Asset Lease",
            "reference_name": lease.name,
            "cost_center": lease.cost_center
        })
    
    # Debit: Interest Expense
    if flt(schedule.interest_amount) > 0:
        interest_account = lease.interest_expense_account or frappe.db.get_value("Company", lease.company, "default_expense_account")
        
        je.append("accounts", {
            "account": interest_account,
            "debit_in_account_currency": flt(schedule.interest_amount),
            "reference_type": "Fixed Asset Lease",
            "reference_name": lease.name,
            "cost_center": lease.cost_center
        })
    
    # Credit: Cash/Bank
    default_cash_account = frappe.db.get_value("Company", lease.company, "default_cash_account")
    
    je.append("accounts", {
        "account": default_cash_account,
        "credit_in_account_currency": flt(schedule.payment_amount),
        "reference_type": "Fixed Asset Lease",
        "reference_name": lease.name,
        "cost_center": lease.cost_center
    })
    
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    
    schedule.journal_entry = je.name


@frappe.whitelist()
def terminate_lease(doc_name, termination_details):
    """Terminate lease early"""
    import json
    if isinstance(termination_details, str):
        termination_details = json.loads(termination_details)
    
    lease = frappe.get_doc("Fixed Asset Lease", doc_name)
    
    if lease.lease_status not in ["Active", "Grace Period"]:
        frappe.throw(_("Only active leases can be terminated"))
    
    termination_date = termination_details.get("termination_date")
    
    if getdate(termination_date) >= getdate(lease.lease_end_date):
        frappe.throw(_("Termination date must be before lease end date"))
    
    # Update lease status
    lease.lease_status = "Terminated"
    lease.termination_date = termination_date
    lease.termination_reason = termination_details.get("termination_reason")
    
    lease.add_comment("Comment", f"Lease terminated early on {termination_date}. Reason: {termination_details.get('termination_reason')}")
    lease.save()
    
    # Update asset status
    lease.revert_asset_lease_status()
    
    # Handle penalty if applicable
    penalty = flt(termination_details.get("early_termination_penalty"))
    if penalty > 0:
        create_termination_penalty_entry(lease, termination_date, penalty)
    
    return True


def create_termination_penalty_entry(lease, termination_date, penalty):
    """Create journal entry for early termination penalty"""
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = termination_date
    je.company = lease.company
    je.user_remark = f"Early Termination Penalty - {lease.asset_name}"
    
    # Debit: Expense Account
    expense_account = lease.lease_expense_account or frappe.db.get_value("Company", lease.company, "default_expense_account")
    
    je.append("accounts", {
        "account": expense_account,
        "debit_in_account_currency": penalty,
        "reference_type": "Fixed Asset Lease",
        "reference_name": lease.name,
        "cost_center": lease.cost_center
    })
    
    # Credit: Cash/Bank
    default_cash_account = frappe.db.get_value("Company", lease.company, "default_cash_account")
    
    je.append("accounts", {
        "account": default_cash_account,
        "credit_in_account_currency": penalty,
        "reference_type": "Fixed Asset Lease",
        "reference_name": lease.name,
        "cost_center": lease.cost_center
    })
    
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()


@frappe.whitelist()
def renew_lease(source_name):
    """Create a new lease based on existing lease"""
    from frappe.model.mapper import get_mapped_doc
    
    def set_missing_values(source, target):
        target.lease_status = "Draft"
        target.docstatus = 0
        
        # Clear old references
        target.journal_entry = None
        target.lease_payment_schedule = []
    
    target_doc = get_mapped_doc("Fixed Asset Lease", source_name, {
        "Fixed Asset Lease": {
            "doctype": "Fixed Asset Lease",
            "field_no_map": [
                "journal_entry",
                "lease_payment_schedule"
            ]
        }
    }, None, set_missing_values)
    
    return target_doc


@frappe.whitelist()
def update_lease_status(doc_name):
    """Update lease status based on dates"""
    lease = frappe.get_doc("Fixed Asset Lease", doc_name)
    
    today = getdate(nowdate())
    
    if lease.lease_status == "Terminated" or lease.lease_status == "Cancelled":
        return
    
    if getdate(lease.lease_end_date) < today:
        lease.lease_status = "Expired"
    elif date_diff(lease.lease_end_date, today) <= 30:
        lease.lease_status = "Expiring Soon"
    elif getdate(lease.lease_start_date) <= today <= getdate(lease.lease_end_date):
        lease.lease_status = "Active"
    
    lease.save()
    
    return lease.lease_status


@frappe.whitelist()
def get_lease_expiring_soon(company=None, days=30):
    """Get leases expiring within specified days"""
    filters = {
        "docstatus": 1,
        "lease_status": "Active",
        "lease_end_date": ["between", [nowdate(), add_days(nowdate(), cint(days))]]
    }
    
    if company:
        filters["company"] = company
    
    expiring_leases = frappe.get_all("Fixed Asset Lease",
        filters=filters,
        fields=[
            "name", "asset", "asset_name", "lease_type", 
            "lessor", "lessee", "lease_end_date", "lease_payment_amount"
        ],
        order_by="lease_end_date"
    )
    
    return expiring_leases