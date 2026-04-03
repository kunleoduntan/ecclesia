# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# ========================================
# ACCRUALS MANAGEMENT SYSTEM - ENHANCED SERVER SCRIPT
# Production Ready with Intelligence & Validation
# File: accruals.py
# ========================================

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, add_days, nowdate, get_last_day, get_first_day
from frappe.model.document import Document
from datetime import datetime, timedelta
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class Accruals(Document):

    # ========================================
    # DOCUMENT HOOKS
    # ========================================

    def validate(self):
        self.validate_accounting_dimensions()
        self.validate_duplicate_references()
        self.validate_account_combinations()
        self.validate_date_logic()
        self.validate_currency_consistency()
        self.auto_suggest_improvements()
        self.calculate_totals()
        self.generate_title()

    def before_save(self):
        self.calculate_totals()
        self.validate_mandatory_fields()
        self.auto_populate_fields()

    def on_submit(self):
        if self.process_accruals:
            self.validate_before_processing()
            self.create_journal_entries()
            self.create_amortization_entries()
            self.update_status_log()
            
            # FIX: Properly handle None values
            journal_count = self.get_journal_count()
            if journal_count is None:
                journal_count = 0
                
            frappe.msgprint(
                _("✨ {0} journal entries created successfully!").format(journal_count), 
                indicator='green',
                alert=True
            )

    def on_cancel(self):
        self.cancel_related_journals()
        self.log_cancellation()

    # ========================================
    # INTELLIGENT AUTO-POPULATION
    # ========================================

    def auto_populate_fields(self):
        """Intelligently populate fields based on context"""
        for row in self.accrued_expense_schedule:
            # Auto-detect WHT applicability
            if not row.charge_wht and row.payable_to:
                row.charge_wht = self.should_apply_wht(row.payable_to)
            
            # Auto-populate WHT account if not set
            if row.charge_wht and not row.wht_account:
                row.wht_account = self.get_default_wht_account(row.payable_to)
                row.wht_rate = self.get_default_wht_rate(row.payable_to)
            
            # Auto-populate deferred account for prepayments
            if row.trans_type == "ACCRUAL & PREPAY" and not row.deferred_expense_account:
                row.deferred_expense_account = self.get_default_deferred_account()
            
            # Generate smart description if empty
            if not row.description:
                row.description = self.generate_smart_description(row)
            
            # Set default currency to company currency if not set
            if not row.currency:
                row.currency = self.get_company_currency()
            
            # Set exchange rate to 1 if currency matches company currency
            if row.currency == self.get_company_currency() and not row.exch_rate:
                row.exch_rate = 1.0

    def get_company_currency(self):
        """Get company's default currency"""
        if not self.company:
            return "NGN"  # Default fallback
        
        company_currency = frappe.db.get_value("Company", self.company, "default_currency")
        return company_currency or "NGN"  # Fallback to NGN if not set

    def should_apply_wht(self, payable_to):
        """Determine if WHT should be applied based on supplier/payee"""
        if not payable_to:
            return False
        
        # Check if it's a registered company (Limited/Ltd)
        if any(term in payable_to.lower() for term in ['limited', 'ltd', 'plc', 'inc']):
            return True
        
        # Check supplier master if exists
        if frappe.db.exists('Supplier', payable_to):
            supplier = frappe.get_doc('Supplier', payable_to)
            if hasattr(supplier, 'tax_withholding_category'):
                return bool(supplier.tax_withholding_category)
        
        return False

    def get_default_wht_account(self, payable_to):
        """Get appropriate WHT account based on supplier type"""
        is_company = any(term in (payable_to or '').lower() for term in ['limited', 'ltd', 'plc'])
        
        # Try to find account dynamically
        account_filter = {
            'company': self.company,
            'account_type': 'Tax',
            'is_group': 0
        }
        
        if is_company:
            account_filter['account_name'] = ['like', '%WHT%Federal%']
        else:
            account_filter['account_name'] = ['like', '%WHT%State%']
        
        accounts = frappe.get_all('Account', filters=account_filter, fields=['name'], limit=1)
        
        if accounts:
            return accounts[0].name
        
        # Fallback to hardcoded if dynamic search fails
        return '4103 - WHT Payable - FGN - 2CES' if is_company else '4102 - WHT Payable - State - 2CES'

    def get_default_wht_rate(self, payable_to):
        """Get appropriate WHT rate"""
        is_company = any(term in (payable_to or '').lower() for term in ['limited', 'ltd', 'plc'])
        return 5 if is_company else 10

    def get_default_deferred_account(self):
        """Get default deferred expense account"""
        account = frappe.get_all(
            'Account',
            filters={
                'company': self.company,
                'account_type': 'Prepaid Expenses',
                'is_group': 0
            },
            fields=['name'],
            limit=1
        )
        return account[0].name if account else None

    def generate_smart_description(self, row):
        """Generate intelligent description based on row data"""
        parts = []
        
        if row.trans_type:
            parts.append(str(row.trans_type))  # FIX: Ensure it's a string
        
        if row.payable_to:
            parts.append(f"for {str(row.payable_to)}")  # FIX: Ensure it's a string
        
        if row.frequency and row.frequency != "NA":
            parts.append(f"({str(row.frequency)})")  # FIX: Ensure it's a string
        
        if self.month:
            parts.append(f"- {str(self.month)}")  # FIX: Ensure it's a string
        
        return " ".join(parts) if parts else "Accrual Entry"

    # ========================================
    # ENHANCED VALIDATIONS
    # ========================================

    def validate_account_combinations(self):
        """Validate that account combinations make accounting sense"""
        for row in self.accrued_expense_schedule:
            if row.dr_account and row.cr_account:
                dr_type = frappe.db.get_value('Account', row.dr_account, 'root_type')
                cr_type = frappe.db.get_value('Account', row.cr_account, 'root_type')
                
                # Warn if both accounts are of same type
                if dr_type == cr_type:
                    frappe.msgprint(
                        _("Row #{0}: Warning - Both Dr and Cr accounts are {1} type. Please verify.")
                        .format(row.idx, dr_type),
                        indicator='orange'
                    )
                
                # Validate expense accruals
                if row.trans_type == "ACCRUAL":
                    if dr_type != 'Expense':
                        frappe.msgprint(
                            _("Row #{0}: Typically Dr Account should be Expense for accruals")
                            .format(row.idx),
                            indicator='orange'
                        )
                    if cr_type != 'Liability':
                        frappe.msgprint(
                            _("Row #{0}: Typically Cr Account should be Liability for accruals")
                            .format(row.idx),
                            indicator='orange'
                        )

    def validate_date_logic(self):
        """Validate date sequences and periods"""
        for row in self.accrued_expense_schedule:
            if row.start_date and row.end_date:
                if getdate(row.start_date) > getdate(row.end_date):
                    frappe.throw(
                        _("Row #{0}: Start Date cannot be after End Date")
                        .format(row.idx)
                    )
            
            if row.posting_date and self.reporting_date:
                if getdate(row.posting_date) > getdate(self.reporting_date):
                    frappe.msgprint(
                        _("Row #{0}: Posting Date is after Reporting Date")
                        .format(row.idx),
                        indicator='orange'
                    )

    def validate_currency_consistency(self):
        """Ensure currency and exchange rate consistency"""
        company_currency = self.get_company_currency()
        
        for row in self.accrued_expense_schedule:
            if not row.currency:
                frappe.throw(
                    _("Row #{0}: Currency is required").format(row.idx)
                )
            
            if row.currency == company_currency and flt(row.exch_rate) != 1:
                frappe.msgprint(
                    _("Row #{0}: Exchange rate for company currency ({1}) should be 1")
                    .format(row.idx, company_currency),
                    indicator='orange'
                )
            
            if row.currency != company_currency and not row.exch_rate:
                frappe.throw(
                    _("Row #{0}: Exchange rate is mandatory for foreign currency")
                    .format(row.idx)
                )

    def validate_before_processing(self):
        """Final validation before creating journal entries"""
        if not self.accrued_expense_schedule:
            frappe.throw(_("Cannot process empty accruals schedule"))
        
        # Check for duplicate journal entries
        existing = frappe.get_all(
            'Journal Entry',
            filters={
                'company': self.company,
                'reference_document_no': self.name,
                'docstatus': 1
            }
        )
        
        if existing:
            frappe.throw(
                _("Journal entries already exist for this document. Cancel them first to reprocess.")
            )

    # ========================================
    # INTELLIGENT SUGGESTIONS
    # ========================================

    def auto_suggest_improvements(self):
        """Provide intelligent suggestions to improve data quality"""
        suggestions = []
        company_currency = self.get_company_currency()
        
        for row in self.accrued_expense_schedule:
            # Suggest frequency for prepayments
            if row.trans_type == "ACCRUAL & PREPAY" and not row.frequency:
                suggestions.append(
                    _("Row #{0}: Consider setting frequency for automatic amortization")
                    .format(row.idx)
                )
            
            # Suggest cost center for expense accounts
            if row.dr_account:
                acc_type = frappe.db.get_value('Account', row.dr_account, 'root_type')
                if acc_type == 'Expense' and not row.cost_center:
                    suggestions.append(
                        _("Row #{0}: Cost center recommended for expense accounts")
                        .format(row.idx)
                    )
            
            # Warn about large amounts
            if flt(row.lc_amount) > 10000000:  # 10M threshold
                suggestions.append(
                    _("Row #{0}: Large amount detected ({1:,.2f} {2}). Please verify.")
                    .format(row.idx, row.lc_amount or 0, company_currency)
                )
            
            # Warn about foreign currency without exchange rate
            if row.currency != company_currency and not row.exch_rate:
                suggestions.append(
                    _("Row #{0}: Exchange rate needed for foreign currency ({1} to {2})")
                    .format(row.idx, row.currency or '', company_currency)
                )
        
        if suggestions:
            frappe.msgprint(
                "<br>".join(suggestions),
                title=_("💡 Smart Suggestions"),
                indicator='blue'
            )

    # ========================================
    # ACCOUNTING DIMENSIONS - FIXED
    # ========================================

    def get_accounting_dimensions(self):
        """Get accounting dimensions with proper handling of dimension defaults"""
        dimensions = []
        
        # Get all enabled accounting dimensions
        accounting_dimensions = frappe.get_all(
            'Accounting Dimension',
            filters={'disabled': 0},
            fields=['fieldname', 'label', 'document_type']
        )
        
        for dim in accounting_dimensions:
            # Get dimension defaults for this dimension
            defaults = frappe.get_all(
                'Dimension Defaults',
                filters={'parent': dim.fieldname, 'parenttype': 'Accounting Dimension'},
                fields=['mandatory_for_bs', 'mandatory_for_pl']
            )
            
            if defaults:
                # Add the default values to the dimension dict
                dim_dict = dim.copy()
                dim_dict['mandatory_for_bs'] = defaults[0].get('mandatory_for_bs', 0)
                dim_dict['mandatory_for_pl'] = defaults[0].get('mandatory_for_pl', 0)
                dimensions.append(dim_dict)
            else:
                # If no defaults, assume not mandatory
                dim_dict = dim.copy()
                dim_dict['mandatory_for_bs'] = 0
                dim_dict['mandatory_for_pl'] = 0
                dimensions.append(dim_dict)
        
        return dimensions

    def validate_accounting_dimensions(self):
        """Validate accounting dimensions based on their defaults"""
        dimensions = self.get_accounting_dimensions()

        for row in self.accrued_expense_schedule:
            for dim in dimensions:
                fieldname = dim.fieldname

                if not hasattr(row, fieldname):
                    continue
                
                # Get account root type
                if row.dr_account:
                    try:
                        account = frappe.get_doc('Account', row.dr_account)
                        
                        # Check if dimension is mandatory for this account type
                        if account.root_type == 'Equity' and dim.get('mandatory_for_bs'):
                            if not row.get(fieldname):
                                frappe.throw(
                                    _("Row #{0}: {1} is mandatory for Balance Sheet accounts")
                                    .format(row.idx, dim.label)
                                )
                        
                        if account.root_type in ['Income', 'Expense'] and dim.get('mandatory_for_pl'):
                            if not row.get(fieldname):
                                frappe.throw(
                                    _("Row #{0}: {1} is mandatory for P&L accounts")
                                    .format(row.idx, dim.label)
                                )
                    except Exception:
                        # Skip if account not found
                        pass

    # ========================================
    # CALCULATIONS
    # ========================================

    def calculate_totals(self):
        total_accrued = 0
        total_wht = 0
        total_charged = 0
        entry_count = 0

        for row in self.accrued_expense_schedule:
            total_accrued += flt(row.lc_amount) or 0
            total_wht += flt(row.wh_tax) or 0
            total_charged += flt(row.periodic_charge) or 0
            entry_count += 1

        self.total_accrued_amount = total_accrued
        self.total_wht = total_wht
        self.total_charged_amount = total_charged
        self.total_entries = entry_count

    def generate_title(self):
        """Generate document title - FIXED to handle None values"""
        try:
            if self.month and self.company:
                self.title = f"{self.month} Accruals - {self.company}"
            elif self.reporting_date:
                month = frappe.utils.get_datetime(self.reporting_date).strftime('%B %Y')
                self.title = f"{month} Accruals"
            else:
                self.title = f"Accruals - {self.name}"
        except Exception as e:
            # Fallback title if there's an error
            self.title = f"Accruals - {self.name}"

    # ========================================
    # ENHANCED VALIDATIONS
    # ========================================

    def validate_mandatory_fields(self):
        if not self.reporting_date:
            frappe.throw(_("Reporting Date is mandatory"))

        if not self.company:
            frappe.throw(_("Company is mandatory"))

        if not self.accrued_expense_schedule:
            frappe.throw(_("Please add at least one accrual entry"))

        for row in self.accrued_expense_schedule:
            if not row.payable_to:
                frappe.throw(_("Row #{0}: Payable To is mandatory").format(row.idx))

            if not row.dr_account:
                frappe.throw(_("Row #{0}: Dr Account is mandatory").format(row.idx))

            if not row.cr_account:
                frappe.throw(_("Row #{0}: Cr Account is mandatory").format(row.idx))

            if flt(row.gross_amount) <= 0:
                frappe.throw(_("Row #{0}: Gross Amount must be greater than 0").format(row.idx))
            
            # Validate prepayment specific fields
            if row.trans_type == "ACCRUAL & PREPAY":
                if not row.deferred_expense_account:
                    frappe.throw(
                        _("Row #{0}: Deferred Expense Account is mandatory for prepayments")
                        .format(row.idx)
                    )
                
                if row.option == "Recur" and not row.frequency:
                    frappe.throw(
                        _("Row #{0}: Frequency is mandatory for recurring prepayments")
                        .format(row.idx)
                    )

    def validate_duplicate_references(self):
        references = {}

        for row in self.accrued_expense_schedule:
            ref = row.name[-7:].upper() if row.name else None

            if ref:
                if ref in references:
                    frappe.throw(
                        _("Duplicate reference {0} found in rows {1} and {2}")
                        .format(ref, references[ref], row.idx)
                    )
                references[ref] = row.idx

    # ========================================
    # JOURNAL ENTRY CREATION
    # ========================================

    def check_is_group_account(self, account):
        if not account:
            return
            
        is_group = frappe.db.get_value("Account", account, "is_group")
        if is_group:
            frappe.throw(
                _("The account {0} is a group account and cannot be used for posting transactions")
                .format(account)
            )

    def add_dimensions_to_entry(self, entry, row):
        dimensions = self.get_accounting_dimensions()

        for dim in dimensions:
            fieldname = dim.fieldname
            if hasattr(row, fieldname) and row.get(fieldname):
                entry[fieldname] = row.get(fieldname)

    def create_journal_entries(self):
        existing_entries = frappe.get_all(
            'Journal Entry',
            filters={'company': self.company, 'reference_document_no': self.name},
            fields=['name']
        )

        if existing_entries:
            frappe.msgprint(_("Journal entries already exist for this batch"))
            return

        created_count = 0
        for row in self.accrued_expense_schedule:
            if row.trans_type in ["ACCRUAL", "ACCRUAL & PREPAY"]:
                self.create_accrual_journal(row)
                created_count += 1
        
        return created_count

    def create_accrual_journal(self, row):
        self.check_is_group_account(row.dr_account)
        self.check_is_group_account(row.cr_account)

        if row.wht_account:
            self.check_is_group_account(row.wht_account)

        accounts = []

        # Debit Entry
        lc_amount = flt(row.lc_amount) or 0
        if lc_amount != 0:
            description = f"{row.description or 'Accrual'} - {row.payable_to or 'Unknown'}"
            debit_entry = {
                "account": row.dr_account,
                "debit_in_account_currency": lc_amount,
                "user_remark": description
            }
            self.add_dimensions_to_entry(debit_entry, row)
            accounts.append(debit_entry)

        # WHT Entry
        wh_tax = flt(row.wh_tax) or 0
        if row.charge_wht and wh_tax != 0:
            description = f"WHT - {row.description or 'Accrual'} - {row.payable_to or 'Unknown'}"
            wht_entry = {
                "account": row.wht_account,
                "credit_in_account_currency": wh_tax,
                "user_remark": description
            }
            self.add_dimensions_to_entry(wht_entry, row)
            accounts.append(wht_entry)

        # Credit Entry (Liability)
        net_amount = flt(row.net_amount) if row.charge_wht else lc_amount

        if net_amount != 0:
            description = f"{row.description or 'Accrual'} - {row.payable_to or 'Unknown'}"
            credit_entry = {
                "account": row.cr_account,
                "credit_in_account_currency": flt(net_amount),
                "party_type": "Supplier" if frappe.db.exists('Supplier', row.payable_to) else None,
                "party": row.payable_to if frappe.db.exists('Supplier', row.payable_to) else None,
                "user_remark": description
            }
            self.add_dimensions_to_entry(credit_entry, row)
            accounts.append(credit_entry)

        if accounts:
            posting_date = row.posting_date or self.reporting_date or nowdate()
            description = f"{row.description or 'Accrual'} - {row.payable_to or 'Unknown'}"
            
            journal_entry = frappe.get_doc({
                'doctype': 'Journal Entry',
                'voucher_type': 'Journal Entry',
                'company': self.company,
                'posting_date': posting_date,
                'naming_series': "ACC-JV-.YYYY.-",
                'user_remark': description,
                'reference_document_no': self.name,
                'accounts': accounts
            })

            journal_entry.insert(ignore_permissions=True)

    # ========================================
    # AMORTIZATION
    # ========================================

    def create_amortization_entries(self):
        for row in self.accrued_expense_schedule:
            if (row.option == "Recur" and row.frequency and 
                row.trans_type == "ACCRUAL & PREPAY" and row.no_of_periods):
                self.create_amortization_schedule(row)

    def create_amortization_schedule(self, row):
        periods = int(row.no_of_periods) if row.no_of_periods else 0
        if periods == 0:
            return

        next_schedule_value = int(row.next_schedule) if row.next_schedule else 1

        for i in range(periods):
            if row.frequency == "Freehand":
                next_due_date = add_months(getdate(row.start_date), i)
            else:
                next_due_date = add_months(
                    getdate(row.start_date),
                    (i + 1) * next_schedule_value
                )

            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.voucher_type = "Journal Entry"
            journal_entry.company = self.company
            journal_entry.posting_date = next_due_date
            journal_entry.user_remark = f"{row.description or 'Accrual'} - Period {i+1}/{periods}"
            journal_entry.reference_document_no = self.name

            # Debit (Expense Recognition)
            periodic_charge = flt(row.periodic_charge) or 0
            if periodic_charge > 0:
                debit_entry = {
                    "account": row.dr_account,
                    "debit_in_account_currency": periodic_charge,
                    "user_remark": f"{row.description or 'Accrual'} - Period {i+1}"
                }
                self.add_dimensions_to_entry(debit_entry, row)
                journal_entry.append("accounts", debit_entry)

                # Credit (Deferred Expense Reduction)
                credit_entry = {
                    "account": row.deferred_expense_account,
                    "credit_in_account_currency": periodic_charge,
                    "user_remark": f"{row.description or 'Accrual'} - Period {i+1}"
                }
                self.add_dimensions_to_entry(credit_entry, row)
                journal_entry.append("accounts", credit_entry)

                journal_entry.insert(ignore_permissions=True)

    # ========================================
    # UTILITIES
    # ========================================

    def get_journal_count(self):
        """Get count of created journal entries"""
        try:
            return frappe.db.count(
                'Journal Entry',
                filters={'reference_document_no': self.name}
            )
        except Exception:
            return 0

    def update_status_log(self):
        """Log processing status - FIXED to handle None"""
        current_log = self.status_log or ""
        log_entry = f"{nowdate()} - Processed by {frappe.session.user}\n"
        self.db_set('status_log', current_log + log_entry, update_modified=False)

    def log_cancellation(self):
        """Log cancellation - FIXED to handle None"""
        current_log = self.status_log or ""
        log_entry = f"{nowdate()} - Cancelled by {frappe.session.user}\n"
        self.db_set('status_log', current_log + log_entry, update_modified=False)

    # ========================================
    # CANCEL
    # ========================================

    def cancel_related_journals(self):
        related_journals = frappe.get_all(
            "Journal Entry",
            filters={"reference_document_no": self.name},
            fields=["name", "docstatus"]
        )

        cancelled_count = 0
        for entry in related_journals:
            try:
                journal = frappe.get_doc("Journal Entry", entry.name)

                if journal.docstatus == 1:
                    journal.cancel()
                    frappe.delete_doc("Journal Entry", entry.name, force=1)
                    cancelled_count += 1
                else:
                    frappe.delete_doc("Journal Entry", entry.name)
            except Exception as e:
                frappe.log_error(f"Error cancelling journal {entry.name}: {str(e)}")

        if cancelled_count:
            frappe.msgprint(
                _("Cancelled {0} journal entries").format(cancelled_count),
                indicator='orange'
            )


# ========================================
# API METHODS - INCLUDING MISSING process_accruals
# ========================================

@frappe.whitelist()
def process_accruals(accrual_doc):
    """
    Process accruals and create journal entries
    Called from the UI when "Process Accruals" button is clicked
    """
    try:
        # Get the accrual document
        doc = frappe.get_doc('Accruals', accrual_doc)
        
        # Validate document status
        if doc.docstatus != 1:
            frappe.throw(_("Accruals document must be submitted before processing"))
        
        if doc.process_accruals:
            frappe.throw(_("Accruals have already been processed"))
        
        # Create journal entries
        created_count = doc.create_journal_entries()
        
        # Create amortization entries if applicable
        doc.create_amortization_entries()
        
        # Update status
        doc.db_set('process_accruals', 1)
        doc.update_status_log()
        
        # Get final count of journal entries
        journal_count = doc.get_journal_count()
        
        return {
            'success': True,
            'message': _('Successfully created {0} journal entries').format(journal_count),
            'created_count': created_count,
            'journal_count': journal_count
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Accruals Processing Error")
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def get_exchange_rate(currency, date=None, company=None):
    """Get exchange rate for a currency, using company's default currency as target"""
    if not company:
        company = frappe.defaults.get_user_default("company")
    
    if not company:
        frappe.throw(_("Please select a company first"))
    
    # Get company's default currency
    company_currency = frappe.db.get_value("Company", company, "default_currency")
    
    if not company_currency:
        company_currency = "NGN"  # Default fallback
    
    if currency == company_currency:
        return 1.0
    
    date = date or nowdate()
    
    # Try to get from Currency Exchange
    rate = frappe.db.get_value(
        'Currency Exchange',
        {
            'from_currency': currency,
            'to_currency': company_currency,
            'date': ['<=', date]
        },
        'exchange_rate',
        order_by='date desc'
    )
    
    return flt(rate) if rate else 0.0


@frappe.whitelist()
def get_supplier_details(supplier):
    """Get supplier details for auto-population"""
    if not frappe.db.exists('Supplier', supplier):
        return {}
    
    supplier_doc = frappe.get_doc('Supplier', supplier)
    
    return {
        'tax_category': supplier_doc.get('tax_withholding_category'),
        'default_currency': supplier_doc.get('default_currency', 'NGN'),
        'is_company': 'limited' in (supplier or '').lower() or 'ltd' in (supplier or '').lower()
    }


@frappe.whitelist()
def preview_journal_entries(accrual_doc_name):
    """Preview journal entries that will be created"""
    try:
        doc = frappe.get_doc('Accruals', accrual_doc_name)
        
        preview = []
        for row in doc.accrued_expense_schedule:
            entry = {
                'payable_to': row.payable_to or '',
                'dr_account': row.dr_account or '',
                'cr_account': row.cr_account or '',
                'amount': flt(row.lc_amount) or 0,
                'wht': flt(row.wh_tax) if row.charge_wht else 0,
                'net': flt(row.net_amount) if row.charge_wht else flt(row.lc_amount) or 0,
                'currency': doc.get_company_currency()
            }
            preview.append(entry)
        
        return preview
    except Exception as e:
        frappe.log_error(f"Error in preview_journal_entries: {str(e)}")
        return []


@frappe.whitelist()
def export_to_excel(accrual_doc_name):
    """Export accruals to beautifully formatted Excel file"""
    try:
        doc = frappe.get_doc('Accruals', accrual_doc_name)
        company_currency = doc.get_company_currency()
        
        # Create workbook and worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Accruals Report"
        
        # Define styles
        header_font = Font(name='Calibri', size=12, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        subheader_font = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
        subheader_fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
        
        data_font = Font(name='Calibri', size=10)
        currency_font = Font(name='Calibri', size=10, color="000080")
        bold_font = Font(name='Calibri', size=10, bold=True)
        
        total_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Set column widths
        column_widths = {
            'A': 5,    # No.
            'B': 25,   # Payable To
            'C': 20,   # Transaction Type
            'D': 35,   # Description
            'E': 12,   # Currency
            'F': 18,   # Gross Amount
            'G': 15,   # Exchange Rate
            'H': 18,   # LC Amount ({company_currency})
            'I': 12,   # WHT Rate %
            'J': 18,   # WHT Amount
            'K': 18,   # Net Amount
            'L': 25,   # Debit Account
            'M': 25,   # Credit Account
            'N': 15,   # Frequency
            'O': 12,   # No. of Periods
            'P': 18,   # Periodic Charge
            'Q': 20,   # Cost Center
            'R': 20,   # Project
        }
        
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
        
        # ========================================
        # HEADER SECTION
        # ========================================
        ws.merge_cells('A1:R1')
        ws['A1'] = f"ACCRUALS REPORT - {doc.company or 'Unknown'}"
        ws['A1'].font = Font(name='Calibri', size=16, bold=True, color="000080")
        ws['A1'].alignment = Alignment(horizontal="center")
        
        ws.merge_cells('A2:R2')
        ws['A2'] = f"Reporting Period: {doc.month or 'Not specified'}"
        ws['A2'].font = Font(name='Calibri', size=12, bold=True)
        ws['A2'].alignment = Alignment(horizontal="center")
        
        ws.merge_cells('A3:R3')
        ws['A3'] = f"Reporting Date: {doc.reporting_date or 'Not specified'}"
        ws['A3'].font = Font(name='Calibri', size=11)
        ws['A3'].alignment = Alignment(horizontal="center")
        
        ws.merge_cells('A4:R4')
        ws['A4'] = f"Document: {doc.name}"
        ws['A4'].font = Font(name='Calibri', size=10, italic=True)
        ws['A4'].alignment = Alignment(horizontal="center")
        
        # ========================================
        # SUMMARY SECTION
        # ========================================
        ws.merge_cells('A6:D6')
        ws['A6'] = "SUMMARY STATISTICS"
        ws['A6'].font = header_font
        ws['A6'].fill = header_fill
        ws['A6'].alignment = header_alignment
        
        summary_data = [
            [f"Total Accrued Amount ({company_currency}):", flt(doc.total_accrued_amount) or 0],
            [f"Total WHT Payable ({company_currency}):", flt(doc.total_wht) or 0],
            [f"Total Charged Amount ({company_currency}):", flt(doc.total_charged_amount) or 0],
            ["Total Entries:", flt(doc.total_entries) or 0]
        ]
        
        for i, (label, value) in enumerate(summary_data, start=7):
            ws[f'A{i}'] = label
            ws[f'A{i}'].font = bold_font
            
            ws[f'B{i}'] = flt(value)
            ws[f'B{i}'].font = currency_font
            ws[f'B{i}'].number_format = '#,##0.00'
            
            if i < len(summary_data) + 6:
                ws[f'A{i}'].border = border
                ws[f'B{i}'].border = border
        
        # ========================================
        # DETAILED ENTRIES SECTION
        # ========================================
        start_row = len(summary_data) + 9
        
        # Table headers - Updated to show company currency
        headers = [
            "No.", "Payable To", "Transaction Type", "Description", "Currency",
            "Gross Amount", "Exchange Rate", f"LC Amount ({company_currency})", "WHT Rate %",
            f"WHT Amount ({company_currency})", f"Net Amount ({company_currency})", 
            "Debit Account", "Credit Account", "Frequency", "No. of Periods", 
            f"Periodic Charge ({company_currency})", "Cost Center", "Project"
        ]
        
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=start_row, column=col_idx, value=header)
            cell.font = subheader_font
            cell.fill = subheader_fill
            cell.alignment = header_alignment
            cell.border = border
        
        # Table data
        row_num = start_row + 1
        grand_totals = {
            'gross': 0,
            'lc_amount': 0,
            'wht': 0,
            'net': 0
        }
        
        for idx, row in enumerate(doc.accrued_expense_schedule, start=1):
            # Get account names if available
            dr_account_name = ""
            cr_account_name = ""
            if row.dr_account:
                dr_account_name = frappe.db.get_value('Account', row.dr_account, 'account_name') or row.dr_account
            if row.cr_account:
                cr_account_name = frappe.db.get_value('Account', row.cr_account, 'account_name') or row.cr_account
            
            data_row = [
                idx,
                row.payable_to or "",
                row.trans_type or "",
                row.description or "",
                row.currency or company_currency,
                flt(row.gross_amount) or 0,
                flt(row.exch_rate) if row.exch_rate else 1.0,
                flt(row.lc_amount) or 0,
                f"{flt(row.wht_rate)}%" if row.charge_wht and row.wht_rate else "N/A",
                flt(row.wh_tax) if row.charge_wht else 0,
                flt(row.net_amount) or 0,
                dr_account_name,
                cr_account_name,
                row.frequency or "NA",
                row.no_of_periods or 0,
                flt(row.periodic_charge) or 0,
                row.cost_center or "",
                row.project or ""
            ]
            
            for col_idx, value in enumerate(data_row, start=1):
                cell = ws.cell(row=row_num, column=col_idx, value=value)
                cell.font = data_font
                cell.border = border
                
                # Format numeric columns
                if col_idx in [6, 7, 8, 10, 11, 16]:  # Amount columns
                    if isinstance(value, (int, float)):
                        cell.number_format = '#,##0.00'
                        cell.font = currency_font
                        cell.alignment = Alignment(horizontal="right")
                
                # Align center for specific columns
                if col_idx in [1, 5, 9, 14, 15]:
                    cell.alignment = Alignment(horizontal="center")
            
            # Accumulate totals
            grand_totals['gross'] += flt(row.gross_amount) or 0
            grand_totals['lc_amount'] += flt(row.lc_amount) or 0
            grand_totals['wht'] += flt(row.wh_tax) if row.charge_wht else 0
            grand_totals['net'] += flt(row.net_amount) or 0
            
            # Apply zebra striping
            if idx % 2 == 0:
                for col in range(1, len(headers) + 1):
                    ws.cell(row=row_num, column=col).fill = PatternFill(
                        start_color="F8F9FA", end_color="F8F9FA", fill_type="solid"
                    )
            
            row_num += 1
        
        # ========================================
        # GRAND TOTALS SECTION
        # ========================================
        total_row = row_num
        
        ws.merge_cells(f'A{total_row}:E{total_row}')
        ws.cell(row=total_row, column=1, value="GRAND TOTALS:").font = bold_font
        ws.cell(row=total_row, column=1).alignment = Alignment(horizontal="right")
        
        # Gross Amount Total
        ws.cell(row=total_row, column=6, value=grand_totals['gross'])
        ws.cell(row=total_row, column=6).font = bold_font
        ws.cell(row=total_row, column=6).number_format = '#,##0.00'
        ws.cell(row=total_row, column=6).fill = total_fill
        
        # Exchange Rate (blank for total)
        ws.cell(row=total_row, column=7, value="").fill = total_fill
        
        # LC Amount Total
        ws.cell(row=total_row, column=8, value=grand_totals['lc_amount'])
        ws.cell(row=total_row, column=8).font = bold_font
        ws.cell(row=total_row, column=8).number_format = '#,##0.00'
        ws.cell(row=total_row, column=8).fill = total_fill
        
        # WHT Rate (blank for total)
        ws.cell(row=total_row, column=9, value="").fill = total_fill
        
        # WHT Total
        ws.cell(row=total_row, column=10, value=grand_totals['wht'])
        ws.cell(row=total_row, column=10).font = bold_font
        ws.cell(row=total_row, column=10).number_format = '#,##0.00'
        ws.cell(row=total_row, column=10).fill = total_fill
        
        # Net Amount Total
        ws.cell(row=total_row, column=11, value=grand_totals['net'])
        ws.cell(row=total_row, column=11).font = bold_font
        ws.cell(row=total_row, column=11).number_format = '#,##0.00'
        ws.cell(row=total_row, column=11).fill = total_fill
        
        # Apply borders to total row
        for col in range(1, 19):
            ws.cell(row=total_row, column=col).border = border
        
        # ========================================
        # FOOTNOTES
        # ========================================
        footnote_row = total_row + 2
        
        footnotes = [
            "Notes:",
            f"1. LC Amount ({company_currency}) = Gross Amount × Exchange Rate",
            f"2. WHT Amount ({company_currency}) = LC Amount × WHT Rate %",
            f"3. Net Amount ({company_currency}) = LC Amount - WHT Amount",
            f"4. Periodic Charge ({company_currency}) = LC Amount ÷ No. of Periods (for prepayments only)",
            f"5. Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"6. Generated by: {frappe.session.user}",
            f"7. Company Currency: {company_currency}"
        ]
        
        for i, note in enumerate(footnotes, start=footnote_row):
            ws.merge_cells(f'A{i}:R{i}')
            ws.cell(row=i, column=1, value=note).font = Font(name='Calibri', size=9, italic=True)
        
        # ========================================
        # SAVE TO TEMPORARY FILE
        # ========================================
        from frappe.utils import get_files_path
        import os
        
        # Create directory if not exists
        export_dir = os.path.join(get_files_path(), "accruals_exports")
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate filename
        filename = f"Accruals_{doc.company or 'Unknown'}_{doc.reporting_date or datetime.now().date()}.xlsx"
        filepath = os.path.join(export_dir, filename)
        
        # Save workbook
        wb.save(filepath)
        
        # Prepare response
        with open(filepath, 'rb') as f:
            file_content = f.read()
        
        # Create File document
        from frappe.utils.file_manager import save_file
        
        file_doc = save_file(
            filename,
            file_content,
            "Accruals",
            doc.name,
            folder="Home",
            is_private=1
        )
        
        # Return download URL
        return {
            'file_url': file_doc.file_url,
            'file_name': filename,
            'message': 'Excel export generated successfully'
        }
        
    except Exception as e:
        frappe.log_error(f"Error in export_to_excel: {str(e)}", "Accruals Export Error")
        frappe.throw(_("Error generating Excel export: {0}").format(str(e)))


@frappe.whitelist()
def get_summary_report(company, reporting_date=None):
    """Get summary report of accruals"""
    filters = {'company': company, 'docstatus': 1}
    
    if reporting_date:
        filters['reporting_date'] = ['<=', reporting_date]
    
    accruals = frappe.get_all(
        'Accruals',
        filters=filters,
        fields=['name', 'month', 'total_accrued_amount', 'total_wht', 'total_charged_amount', 'creation']
    )
    
    return accruals


@frappe.whitelist()
def bulk_process_accruals(accrual_names):
    """Process multiple accruals at once"""
    if isinstance(accrual_names, str):
        try:
            accrual_names = json.loads(accrual_names)
        except Exception:
            accrual_names = [accrual_names]
    
    results = []
    for name in accrual_names:
        try:
            doc = frappe.get_doc('Accruals', name)
            if doc.docstatus == 1 and not doc.process_accruals:
                # Call the process_accruals function
                result = process_accruals(name)
                if result.get('success'):
                    results.append({
                        'name': name,
                        'status': 'Success',
                        'message': result['message']
                    })
                else:
                    results.append({
                        'name': name,
                        'status': 'Error',
                        'message': result['message']
                    })
            else:
                results.append({
                    'name': name,
                    'status': 'Skipped',
                    'message': 'Already processed or not submitted'
                })
        except Exception as e:
            results.append({
                'name': name,
                'status': 'Error',
                'message': str(e)
            })
    
    return results