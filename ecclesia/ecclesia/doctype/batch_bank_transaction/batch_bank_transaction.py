# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt




import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today, add_days, cstr
import json
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import io
import base64


class BatchBankTransaction(Document):
    """
    Batch Bank Transaction Document Controller
    Handles batch processing of bank transactions with AI-powered features
    """
    
    def validate(self):
        """Validate document before saving"""
        self.validate_bank_account()
        self.validate_transactions()
        self.validate_duplicate_references()
        self.calculate_totals()
        self.validate_balance()
        
    def before_submit(self):
        """Actions before submitting"""
        self.validate_all_transactions_complete()
        self.check_posting_restrictions()
        
    def on_submit(self):
        """Actions on submit - Create payment/receipt entries"""
        if self.post_batch:
            self.create_payment_entries()
            self.create_receipt_entries()
            self.update_bank_balance()
            frappe.msgprint(_("Batch posted successfully. {0} entries created.").format(
                len(self.transaction_entry)
            ), indicator='green')
    
    def on_cancel(self):
        """Actions on cancel - Cancel related documents"""
        self.cancel_related_documents()
        frappe.msgprint(_("Batch cancelled and related documents removed."), indicator='orange')
    
    # ========================================
    # VALIDATION METHODS
    # ========================================
    
    def validate_bank_account(self):
        """Validate bank account exists and is active"""
        if not self.bank_account:
            frappe.throw(_("Bank Account is mandatory"))
        
        bank_account = frappe.get_doc("Bank Account", self.bank_account)
        if bank_account.disabled:
            frappe.throw(_("Bank Account {0} is disabled").format(self.bank_account))
    
    def validate_transactions(self):
        """Validate individual transactions"""
        if not self.transaction_entry:
            frappe.throw(_("Please add at least one transaction"))
        
        for idx, row in enumerate(self.transaction_entry):
            # Validate required fields
            if not row.posting_date:
                frappe.throw(_("Row {0}: Posting Date is mandatory").format(idx + 1))
            
            if not row.trans_type:
                frappe.throw(_("Row {0}: Transaction Type is mandatory").format(idx + 1))
            
            if not row.amount or row.amount <= 0:
                frappe.throw(_("Row {0}: Amount must be greater than 0").format(idx + 1))
            
            if not row.party:
                frappe.throw(_("Row {0}: Party is mandatory").format(idx + 1))
            
            # Validate party type matches party
            self.validate_party_type(row, idx)
            
            # Validate date is not future
            if getdate(row.posting_date) > getdate(today()):
                frappe.throw(_("Row {0}: Posting date cannot be in future").format(idx + 1))
    
    def validate_party_type(self, row, idx):
        """Validate party type matches the selected party"""
        if row.party_type and row.party:
            if row.party_type in ["Customer", "Supplier"]:
                if not frappe.db.exists(row.party_type, row.party):
                    frappe.throw(_("Row {0}: {1} {2} does not exist").format(
                        idx + 1, row.party_type, row.party
                    ))
            elif row.party_type == "Account":
                if not frappe.db.exists("Account", row.party):
                    frappe.throw(_("Row {0}: Account {1} does not exist").format(
                        idx + 1, row.party
                    ))
    
    def validate_duplicate_references(self):
        """Check for duplicate reference numbers in the system"""
        for row in self.transaction_entry:
            if row.name:
                ref_no = row.name[-7:].upper()
                
                # Check in Payments
                existing_payment = frappe.db.exists("Payments", {"reference_no": ref_no})
                if existing_payment:
                    frappe.throw(_("Reference number {0} already exists in Payments. This batch may have been posted already.").format(ref_no))
                
                # Check in Receipts
                existing_receipt = frappe.db.exists("Receipts", {"reference_no": ref_no})
                if existing_receipt:
                    frappe.throw(_("Reference number {0} already exists in Receipts. This batch may have been posted already.").format(ref_no))
    
    def calculate_totals(self):
        """Calculate total inflow, outflow and balance"""
        total_inflow = 0
        total_outflow = 0
        balance = flt(self.opening_balance)
        
        for row in self.transaction_entry:
            total_inflow += flt(row.inflow)
            total_outflow += flt(row.outflow)
            balance += flt(row.inflow) - flt(row.outflow)
            row.balance = balance
        
        self.total_inflow = total_inflow
        self.total_outflow = total_outflow
        self.balance = balance
    
    def validate_balance(self):
        """Validate that balance calculations are correct"""
        calculated_balance = flt(self.opening_balance) + flt(self.total_inflow) - flt(self.total_outflow)
        
        if abs(calculated_balance - flt(self.balance)) > 0.01:
            frappe.throw(_("Balance calculation error. Expected {0}, got {1}").format(
                calculated_balance, self.balance
            ))
    
    def validate_all_transactions_complete(self):
        """Validate all transactions have complete information before submit"""
        incomplete = []
        default_cc = frappe.db.get_value("Company", self.company, "cost_center")

        for idx, row in enumerate(self.transaction_entry, start=1):
            # Validate Remark
            if not row.remark or len(row.remark.strip()) < 5:
                incomplete.append(_("Row {0}: Insufficient remark").format(idx))

            # Validate / Auto-set Cost Center
            if not row.cost_center:
                # Auto-assign only
                row.cost_center = default_cc

                # If still missing after auto-assign, then notify
                if not row.cost_center:
                    incomplete.append(_("Row {0}: Cost Center is mandatory").format(idx))

        # Throw aggregated errors
        if incomplete:
            frappe.throw("<br>".join([frappe.bold(msg) for msg in incomplete]))
    
    def check_posting_restrictions(self):
        """Check if posting is allowed for the selected period"""
        from erpnext.accounts.utils import get_fiscal_year
        
        for idx, row in enumerate(self.transaction_entry):
            try:
                fiscal_year = get_fiscal_year(row.posting_date, company=self.company)[0]
            except Exception as e:
                frappe.throw(_("Row {0}: {1}").format(idx + 1, str(e)))
    
    # ========================================
    # PAYMENT/RECEIPT CREATION
    # ========================================
    
    def create_payment_entries(self):
        """Create payment entries for outflow transactions"""
        payment_types = ["Payment", "Supplier Payment", "Transfer Out", "Customer Refunds"]
        
        for row in self.transaction_entry:
            if row.trans_type in payment_types:
                try:
                    if row.trans_type == "Payment":
                        self.create_expense_payment(row)
                    elif row.trans_type == "Supplier Payment":
                        self.create_supplier_payment(row)
                    elif row.trans_type == "Transfer Out":
                        self.create_transfer_out(row)
                    elif row.trans_type == "Customer Refunds":
                        self.create_customer_refund(row)
                except Exception as e:
                    frappe.log_error(f"Error creating payment for {row.name}: {str(e)}")
                    frappe.throw(_("Error creating payment entry for row {0}: {1}").format(
                        row.idx, str(e)
                    ))
    
    def create_expense_payment(self, row):
        """Create expense payment entry"""
        local_currency = frappe.db.get_value("Company", self.company, "default_currency")
        payment = frappe.new_doc('Payments')
        payment.transaction_date = row.posting_date
        payment.payee_name = (row.payee_name or "").title()
        payment.account_to_debit = row.party
        payment.trans_type = "Expense Payment"
        payment.payment_currency = self.bank_account_currency
        payment.cost_center = row.cost_center
        payment.transaction_purposes = (row.remark or "").title()
        payment.mode_of_payment = row.mode_of_payment or "Wire Transfer"
        payment.remittance_bank = self.bank_account
        payment.exchange_rate = 1 if self.bank_account_currency == local_currency else flt(row.exch_rate)
        payment.amount_paid = flt(row.amount) if self.bank_account_currency == local_currency else 0
        payment.amount_paid_in_fc = flt(row.amount_in_fc) if self.bank_account_currency != local_currency else 0
        payment.department = row.department
        payment.customer_id = row.customer_id
        payment.nature_of_expense = "Internal"
        payment.create_accounting_entries = 1
        payment.approval_doc = row.name
        payment.cashflow_type = "Operating costs"
        payment.branch = row.branch
        payment.reference_no = row.name[-7:].upper()
        payment.issued_by = self.batch_owner
        payment.date = today()
        
        payment.insert(ignore_permissions=True)
        payment.submit()
        
        frappe.db.set_value("Transaction Entry", row.name, "payment_entry", payment.name)
    
    def create_supplier_payment(self, row):
        """Create supplier payment entry"""
        local_currency = frappe.db.get_value("Company", self.company, "default_currency")
        payment = frappe.new_doc('Payments')
        payment.transaction_date = row.posting_date
        payment.payee_id = row.party
        payment.payee_name = row.party_name or frappe.db.get_value("Supplier", row.party, "supplier_name")
        payment.trans_type = "Supplier Payment"
        payment.payment_currency = self.bank_account_currency
        payment.cost_center = row.cost_center
        payment.transaction_purposes = (row.remark or "").title()
        payment.mode_of_payment = row.mode_of_payment or "Wire Transfer"
        payment.remittance_bank = self.bank_account
        payment.exchange_rate = 1 if self.bank_account_currency == local_currency else flt(row.exch_rate)
        payment.amount_paid = flt(row.amount) if self.bank_account_currency == local_currency else 0
        payment.amount_paid_in_fc = flt(row.amount_in_fc) if self.bank_account_currency != local_currency else 0
        payment.department = row.department
        payment.customer_id = row.customer_id
        payment.create_accounting_entries = 1
        payment.approval_doc = row.name
        payment.cashflow_type = "Supplier payments"
        payment.branch = row.branch
        payment.reference_no = row.name[-7:].upper()
        payment.issued_by = self.batch_owner
        payment.date = today()
        
        payment.insert(ignore_permissions=True)
        payment.submit()
        
        frappe.db.set_value("Transaction Entry", row.name, "payment_entry", payment.name)
    
    def create_transfer_out(self, row):
        """Create transfer out payment"""
        local_currency = frappe.db.get_value("Company", self.company, "default_currency")
        payment = frappe.new_doc('Payments')
        payment.transaction_date = row.posting_date
        payment.account_to_debit = row.party
        payment.payee_name = row.party
        payment.trans_type = "Transfer Out"
        payment.cost_center = row.cost_center
        payment.payment_currency = self.bank_account_currency
        payment.transaction_purposes = row.remark
        payment.mode_of_payment = "Wire Transfer"
        payment.remittance_bank = self.bank_account
        payment.exchange_rate = 1 if self.bank_account_currency == local_currency else flt(row.exch_rate)
        payment.amount_paid = flt(row.amount) if self.bank_account_currency == local_currency else 0
        payment.amount_paid_in_fc = flt(row.amount_in_fc) if self.bank_account_currency != local_currency else 0
        payment.create_accounting_entries = 1
        payment.approval_doc = row.name
        payment.cashflow_type = "Funds Transfer"
        payment.reference_no = row.name[-7:].upper()
        payment.issued_by = self.batch_owner
        payment.date = today()
        
        payment.insert(ignore_permissions=True)
        payment.submit()
        
        frappe.db.set_value("Transaction Entry", row.name, "payment_entry", payment.name)
    
    def create_customer_refund(self, row):
        """Create customer refund receipt"""
        local_currency = frappe.db.get_value("Company", self.company, "default_currency")
        receipt = frappe.new_doc('Receipts')
        receipt.transaction_date = row.posting_date
        receipt.customer_id = row.party
        receipt.cash_customer_name = row.party
        receipt.customer_type = "Customer Refund"
        receipt.receipt_currency = self.bank_account_currency
        receipt.cost_center = row.cost_center
        receipt.transaction_purposes = (row.remark or "").title()
        receipt.mode_of_payment = row.mode_of_payment or "Wire Transfer"
        receipt.remittance_bank = self.bank_account
        receipt.exchange_rate = 1 if self.bank_account_currency == local_currency else flt(row.exch_rate)
        receipt.amount_received = flt(row.amount) if self.bank_account_currency == local_currency else 0
        receipt.amount_received_in_fc = flt(row.amount_in_fc) if self.bank_account_currency != local_currency else 0
        receipt.department = row.department
        receipt.create_accounting_entries = 1
        receipt.approval_doc = row.name
        receipt.cashflow_type = 'Receipt from Customer'
        receipt.branch = row.branch
        receipt.reference_no = row.name[-7:].upper()
        receipt.issued_by = self.batch_owner
        receipt.date = today()
        
        receipt.insert(ignore_permissions=True)
        receipt.submit()
        
        frappe.db.set_value("Transaction Entry", row.name, "receipt_entry", receipt.name)
    
    def create_receipt_entries(self):
        """Create receipt entries for inflow transactions"""
        receipt_types = ["Customer Receipt", "Receipt", "Transfer In", "Supplier Refunds"]
        
        for row in self.transaction_entry:
            if row.trans_type in receipt_types:
                try:
                    if row.trans_type == "Customer Receipt":
                        self.create_customer_receipt(row)
                    elif row.trans_type == "Receipt":
                        self.create_general_receipt(row)
                    elif row.trans_type == "Transfer In":
                        self.create_transfer_in(row)
                    elif row.trans_type == "Supplier Refunds":
                        self.create_supplier_refund(row)
                except Exception as e:
                    frappe.log_error(f"Error creating receipt for {row.name}: {str(e)}")
                    frappe.throw(_("Error creating receipt entry for row {0}: {1}").format(
                        row.idx, str(e)
                    ))
    
    def create_customer_receipt(self, row):
        """Create customer receipt entry"""
        local_currency = frappe.db.get_value("Company", self.company, "default_currency")
        receipt = frappe.new_doc("Receipts")
        receipt.transaction_date = row.posting_date
        receipt.customer_type = 'Receive from Registered'
        receipt.cost_center = row.cost_center
        receipt.customer_id = row.party
        receipt.create_accounting_entries = 1
        receipt.transaction_purposes = "Received from customer"
        receipt.receipt_currency = self.bank_account_currency or row.transaction_currency
        receipt.exchange_rate = 1 if self.bank_account_currency == local_currency else flt(row.exch_rate)
        receipt.amount_received = flt(row.amount) if self.bank_account_currency == local_currency else 0
        receipt.amount_received_in_fc = flt(row.amount_in_fc) if self.bank_account_currency != local_currency else 0
        receipt.mode_of_payment = row.mode_of_payment or "Wire Transfer"
        receipt.reference_no = row.name[-7:].upper()
        receipt.referenced_document_no = self.name
        receipt.remittance_bank = self.bank_account
        receipt.approval_doc = row.name
        receipt.branch = row.branch
        receipt.issued_by = self.batch_owner
        receipt.date = today()
        
        receipt.insert(ignore_permissions=True)
        receipt.submit()
        
        frappe.db.set_value("Transaction Entry", row.name, "receipt_entry", receipt.name)
    
    def create_general_receipt(self, row):
        """Create general revenue receipt"""
        local_currency = frappe.db.get_value("Company", self.company, "default_currency")
        receipt = frappe.new_doc("Receipts")
        receipt.transaction_date = row.posting_date
        receipt.customer_type = 'Revenue Receipting'
        receipt.account_to_credit = row.party
        receipt.cost_center = row.cost_center
        receipt.cash_customer_name = (row.payee_name or "").title()
        receipt.create_accounting_entries = 1
        receipt.transaction_purposes = f"Received from {row.payee_name} for {row.remark}"
        receipt.receipt_currency = row.transaction_currency
        receipt.exchange_rate = 1 if self.bank_account_currency == local_currency else flt(row.exch_rate)
        receipt.amount_received = flt(row.amount) if self.bank_account_currency == local_currency else 0
        receipt.amount_received_in_fc = flt(row.amount_in_fc) if self.bank_account_currency != local_currency else 0
        receipt.mode_of_payment = row.mode_of_payment or "Wire Transfer"
        receipt.reference_no = row.name[-7:].upper()
        receipt.approval_doc = row.name
        receipt.branch = row.branch
        receipt.referenced_document_no = self.name
        receipt.remittance_bank = self.bank_account
        receipt.issued_by = self.batch_owner
        receipt.date = today()
        
        receipt.insert(ignore_permissions=True)
        receipt.submit()
        
        frappe.db.set_value("Transaction Entry", row.name, "receipt_entry", receipt.name)
    
    def create_transfer_in(self, row):
        """Create transfer in receipt"""
        local_currency = frappe.db.get_value("Company", self.company, "default_currency")
        receipt = frappe.new_doc("Receipts")
        receipt.transaction_date = row.posting_date
        receipt.customer_type = 'Transfer In'
        receipt.account_to_credit = row.party
        receipt.cash_customer_name = row.party
        receipt.cost_center = row.cost_center
        receipt.create_accounting_entries = 1
        receipt.transaction_purposes = row.remark
        receipt.receipt_currency = self.bank_account_currency
        receipt.exchange_rate = 1 if self.bank_account_currency == local_currency else flt(row.exch_rate)
        receipt.amount_received = flt(row.amount) if self.bank_account_currency == local_currency else 0
        receipt.amount_received_in_fc = flt(row.amount_in_fc) if self.bank_account_currency != local_currency else 0
        receipt.mode_of_payment = row.mode_of_payment or "Wire Transfer"
        receipt.account_to_credit = row.party
        receipt.reference_no = row.name[-7:].upper()
        receipt.approval_doc = row.name
        receipt.branch = row.branch
        receipt.referenced_document_no = self.name
        receipt.remittance_bank = self.bank_account
        receipt.issued_by = self.batch_owner
        receipt.date = today()
        
        receipt.insert(ignore_permissions=True)
        receipt.submit()
        
        frappe.db.set_value("Transaction Entry", row.name, "receipt_entry", receipt.name)
    
    def create_supplier_refund(self, row):
        """Create supplier refund payment"""
        local_currency = frappe.db.get_value("Company", self.company, "default_currency")
        payment = frappe.new_doc('Payments')
        payment.transaction_date = row.posting_date
        payment.payee_id = row.party
        payment.trans_type = "Supplier Refunds"
        payment.cost_center = row.cost_center
        payment.payment_currency = self.bank_account_currency
        payment.transaction_purposes = (row.remark or "").title()
        payment.mode_of_payment = "Wire Transfer"
        payment.remittance_bank = self.bank_account
        payment.exchange_rate = 1 if self.bank_account_currency == local_currency else flt(row.exch_rate)
        payment.amount_paid = flt(row.amount) if self.bank_account_currency == local_currency else 0
        payment.amount_paid_in_fc = flt(row.amount_in_fc) if self.bank_account_currency != local_currency else 0
        payment.create_accounting_entries = 1
        payment.approval_doc = row.name
        payment.cashflow_type = "Supplier payments"
        payment.reference_no = row.name[-7:].upper()
        payment.issued_by = self.batch_owner
        payment.date = today()
        
        payment.insert(ignore_permissions=True)
        payment.submit()
        
        frappe.db.set_value("Transaction Entry", row.name, "payment_entry", payment.name)
    
    def update_bank_balance(self):
        """Update bank account balance after posting"""
        # This would integrate with your bank reconciliation module
        pass
    
    def cancel_related_documents(self):
        """Cancel all related payment and receipt entries"""
        # Cancel Journal Entries
        journal_entries = frappe.get_all("Journal Entry", 
            filters={"reference_document_no": self.name, "docstatus": 1},
            fields=["name"])
        
        for je in journal_entries:
            doc = frappe.get_doc("Journal Entry", je.name)
            doc.cancel()
        
        # Cancel Payment Entries
        payment_entries = frappe.get_all("Payment Entry",
            filters={"reference_document_no": self.name, "docstatus": 1},
            fields=["name"])
        
        for pe in payment_entries:
            doc = frappe.get_doc("Payment Entry", pe.name)
            doc.cancel()
        
        # Cancel Payments
        for row in self.transaction_entry:
            if row.payment_entry:
                try:
                    doc = frappe.get_doc("Payments", row.payment_entry)
                    if doc.docstatus == 1:
                        doc.cancel()
                except Exception as e:
                    frappe.log_error(f"Error cancelling payment {row.payment_entry}: {str(e)}")
            
            if row.receipt_entry:
                try:
                    doc = frappe.get_doc("Receipts", row.receipt_entry)
                    if doc.docstatus == 1:
                        doc.cancel()
                except Exception as e:
                    frappe.log_error(f"Error cancelling receipt {row.receipt_entry}: {str(e)}")
        
        # Cancel Auto Repeat documents
        auto_repeats = frappe.get_all("Auto Repeat",
            filters={"reference_document": self.name, "docstatus": 1},
            fields=["name"])
        
        for ar in auto_repeats:
            doc = frappe.get_doc("Auto Repeat", ar.name)
            doc.cancel()


# ========================================
# API METHODS (WHITELISTED)
# ========================================

@frappe.whitelist()
def import_transactions(file_url, has_header=True):
    """
    Import transactions from CSV/Excel file
    
    Args:
        file_url: URL of the uploaded file
        has_header: Boolean indicating if file has header row
    
    Returns:
        List of transaction dictionaries
    """
    try:
        # Get file from URL
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()
        
        transactions = []
        
        # Determine file type and parse accordingly
        if file_path.endswith('.csv'):
            transactions = parse_csv_file(file_path, has_header)
        elif file_path.endswith(('.xlsx', '.xls')):
            transactions = parse_excel_file(file_path, has_header)
        else:
            frappe.throw(_("Unsupported file format. Please upload CSV or Excel file."))
        
        return transactions
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Import Transactions Error")
        frappe.throw(_("Error importing transactions: {0}").format(str(e)))


def parse_csv_file(file_path, has_header):
    """Parse CSV file and return transaction list"""
    import csv
    
    transactions = []
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        
        if has_header:
            next(reader)  # Skip header row
        
        for row in reader:
            if len(row) >= 5:  # Minimum required columns
                transactions.append({
                    'posting_date': row[0],
                    'trans_type': row[1],
                    'party': row[2],
                    'amount': flt(row[3]),
                    'remark': row[4],
                    'payee_name': row[5] if len(row) > 5 else None,
                    'cost_center': row[6] if len(row) > 6 else None
                })
    
    return transactions


def parse_excel_file(file_path, has_header):
    """Parse Excel file and return transaction list"""
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    
    transactions = []
    start_row = 2 if has_header else 1
    
    for row in ws.iter_rows(min_row=start_row, values_only=True):
        if row[0]:  # Check if date exists
            transactions.append({
                'posting_date': cstr(row[0]),
                'trans_type': cstr(row[1]) if row[1] else None,
                'party': cstr(row[2]) if row[2] else None,
                'amount': flt(row[3]),
                'remark': cstr(row[4]) if row[4] else None,
                'payee_name': cstr(row[5]) if len(row) > 5 and row[5] else None,
                'cost_center': cstr(row[6]) if len(row) > 6 and row[6] else None
            })
    
    return transactions


@frappe.whitelist()
def export_to_excel(doc_name):
    """
    Export batch transactions to Excel file
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
    
    Returns:
        Dictionary with file URL
    """
    try:
        doc = frappe.get_doc("Batch Bank Transaction", doc_name)
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"
        
        # Define styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Add batch header info
        ws['A1'] = "Batch Bank Transaction Report"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A2'] = f"Batch Date: {doc.batch_date}"
        ws['A3'] = f"Bank Account: {doc.bank_account}"
        ws['A4'] = f"Currency: {doc.bank_account_currency}"
        ws['A5'] = f"Opening Balance: {doc.opening_balance}"
        
        # Headers for transaction table
        headers = ['#', 'Date', 'Type', 'Party', 'Party Name', 'Amount', 
                   'Inflow', 'Outflow', 'Balance', 'Remark', 'Reference']
        
        row = 7
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Add transaction data
        for idx, trans in enumerate(doc.transaction_entry, start=1):
            row += 1
            data = [
                idx,
                trans.posting_date,
                trans.trans_type,
                trans.party,
                trans.party_name or '',
                trans.amount,
                trans.inflow,
                trans.outflow,
                trans.balance,
                trans.remark or '',
                trans.reference_no or ''
            ]
            
            for col, value in enumerate(data, start=1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border
                
                # Format currency columns
                if col in [6, 7, 8, 9]:
                    cell.number_format = '#,##0.00'
        
        # Add totals row
        row += 1
        ws.cell(row=row, column=1, value="TOTALS").font = Font(bold=True)
        ws.cell(row=row, column=7, value=doc.total_inflow).font = Font(bold=True)
        ws.cell(row=row, column=7).number_format = '#,##0.00'
        ws.cell(row=row, column=8, value=doc.total_outflow).font = Font(bold=True)
        ws.cell(row=row, column=8).number_format = '#,##0.00'
        ws.cell(row=row, column=9, value=doc.balance).font = Font(bold=True)
        ws.cell(row=row, column=9).number_format = '#,##0.00'
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 30
        ws.column_dimensions['E'].width = 25
        ws.column_dimensions['F'].width = 15
        ws.column_dimensions['G'].width = 15
        ws.column_dimensions['H'].width = 15
        ws.column_dimensions['I'].width = 15
        ws.column_dimensions['J'].width = 40
        ws.column_dimensions['K'].width = 12
        
        # Save to BytesIO
        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)
        
        # Create file in ERPNext
        filename = f"Batch_Bank_Transaction_{doc_name}_{today()}.xlsx"
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "content": file_stream.getvalue(),
            "is_private": 1,
            "attached_to_doctype": "Batch Bank Transaction",
            "attached_to_name": doc_name
        })
        file_doc.insert(ignore_permissions=True)
        
        return {
            "file_url": file_doc.file_url,
            "file_name": filename
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Export to Excel Error")
        frappe.throw(_("Error exporting to Excel: {0}").format(str(e)))


@frappe.whitelist()
def get_ai_suggestions(doc_name):
    """
    Get AI-powered suggestions for the batch
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
    
    Returns:
        Dictionary with AI suggestions
    """
    try:
        doc = frappe.get_doc("Batch Bank Transaction", doc_name)
        
        suggestions = {
            "anomalies": detect_anomalies(doc),
            "optimizations": suggest_optimizations(doc),
            "validation_issues": check_validation_issues(doc),
            "duplicate_risks": find_potential_duplicates(doc)
        }
        
        return suggestions
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "AI Suggestions Error")
        return {"error": str(e)}


def detect_anomalies(doc):
    """Detect anomalies in the batch"""
    anomalies = []
    
    if not doc.transaction_entry:
        return anomalies
    
    # Calculate statistics
    amounts = [flt(t.amount) for t in doc.transaction_entry if t.amount]
    if not amounts:
        return anomalies
    
    avg_amount = sum(amounts) / len(amounts)
    
    # Simple standard deviation
    variance = sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)
    std_dev = variance ** 0.5
    
    # Check for outliers (2 standard deviations)
    for idx, trans in enumerate(doc.transaction_entry):
        if flt(trans.amount) > avg_amount + (2 * std_dev):
            anomalies.append({
                "row": idx + 1,
                "type": "large_amount",
                "message": f"Unusually large amount: {frappe.format_value(trans.amount, {'fieldtype': 'Currency'})}",
                "severity": "warning"
            })
        
        # Check for missing critical information
        if not trans.remark or len(trans.remark) < 10:
            anomalies.append({
                "row": idx + 1,
                "type": "insufficient_detail",
                "message": "Insufficient remark detail",
                "severity": "info"
            })
        
        # Check for weekend transactions
        posting_date = getdate(trans.posting_date)
        if posting_date.weekday() >= 5:  # Saturday or Sunday
            anomalies.append({
                "row": idx + 1,
                "type": "weekend_transaction",
                "message": f"Transaction on weekend: {posting_date.strftime('%A, %B %d')}",
                "severity": "info"
            })
    
    return anomalies


def suggest_optimizations(doc):
    """Suggest optimizations for the batch"""
    suggestions = []
    
    # Check for recurring parties
    party_counts = {}
    for trans in doc.transaction_entry:
        if trans.party:
            party_counts[trans.party] = party_counts.get(trans.party, 0) + 1
    
    for party, count in party_counts.items():
        if count >= 3:
            suggestions.append({
                "type": "recurring_party",
                "message": f"Consider setting up recurring transaction for {party} ({count} occurrences)",
                "action": "create_auto_repeat"
            })
    
    # Check for similar amounts
    amount_groups = {}
    for trans in doc.transaction_entry:
        rounded = round(flt(trans.amount) / 1000) * 1000
        if rounded > 0:
            amount_groups[rounded] = amount_groups.get(rounded, 0) + 1
    
    for amount, count in amount_groups.items():
        if count >= 3:
            suggestions.append({
                "type": "similar_amounts",
                "message": f"Multiple transactions around {frappe.format_value(amount, {'fieldtype': 'Currency'})} - consider bulk processing",
                "action": "bulk_process"
            })
    
    # Check if all transactions use same cost center
    cost_centers = set(t.cost_center for t in doc.transaction_entry if t.cost_center)
    if len(cost_centers) == 1:
        suggestions.append({
            "type": "single_cost_center",
            "message": "All transactions use the same cost center - consider setting it at batch level",
            "action": "set_batch_default"
        })
    
    return suggestions


def check_validation_issues(doc):
    """Check for validation issues"""
    issues = []
    
    for idx, trans in enumerate(doc.transaction_entry):
        # Check mandatory fields
        if not trans.posting_date:
            issues.append({
                "row": idx + 1,
                "field": "posting_date",
                "message": "Missing posting date",
                "severity": "error"
            })
        
        if not trans.trans_type:
            issues.append({
                "row": idx + 1,
                "field": "trans_type",
                "message": "Missing transaction type",
                "severity": "error"
            })
        
        if not trans.amount or trans.amount <= 0:
            issues.append({
                "row": idx + 1,
                "field": "amount",
                "message": "Invalid amount",
                "severity": "error"
            })
        
        if not trans.party:
            issues.append({
                "row": idx + 1,
                "field": "party",
                "message": "Missing party",
                "severity": "error"
            })
        
        if not trans.remark:
            issues.append({
                "row": idx + 1,
                "field": "remark",
                "message": "Missing remark",
                "severity": "warning"
            })
        
        # Check for future dates
        if trans.posting_date and getdate(trans.posting_date) > getdate(today()):
            issues.append({
                "row": idx + 1,
                "field": "posting_date",
                "message": "Future date not allowed",
                "severity": "error"
            })
    
    return issues


def find_potential_duplicates(doc):
    """Find potential duplicate transactions"""
    duplicates = []
    seen = {}
    
    for idx, trans in enumerate(doc.transaction_entry):
        key = f"{trans.posting_date}_{trans.party}_{flt(trans.amount)}"
        
        if key in seen:
            duplicates.append({
                "row1": seen[key] + 1,
                "row2": idx + 1,
                "date": trans.posting_date,
                "party": trans.party,
                "amount": trans.amount,
                "confidence": 0.9
            })
        else:
            seen[key] = idx
    
    return duplicates


@frappe.whitelist()
def auto_categorize_transaction(remark):
    """
    Auto-categorize transaction based on remark using AI
    
    Args:
        remark: Transaction remark/description
    
    Returns:
        Dictionary with suggested account and confidence score
    """
    if not remark:
        return None
    
    remark_lower = remark.lower()
    
    # AI categorization rules
    categories = [
        {
            "keywords": ['transport', 'fare', 'uber', 'taxi', 'delivery', 'shipping'],
            "account": '8027 - Transportation expenses',
            "confidence": 0.95
        },
        {
            "keywords": ['airtime', 'telephone', 'cug', 'phone', 'call', 'mobile'],
            "account": '8008 - Telephone expenses',
            "confidence": 0.90
        },
        {
            "keywords": ['fuel', 'fueling', 'petrol', 'diesel', 'gas'],
            "account": '8003 - Vehicle fueling expenses',
            "confidence": 0.92
        },
        {
            "keywords": ['water', 'meal', 'lunch', 'dinner', 'food', 'subsidy'],
            "account": '8006 - Meal expenses',
            "confidence": 0.88
        },
        {
            "keywords": ['stationery', 'paper', 'printing', 'office supplies'],
            "account": '8016 - Printing and stationeries',
            "confidence": 0.85
        },
        {
            "keywords": ['rent', 'lease', 'accommodation', 'housing'],
            "account": '8010 - Rent expenses',
            "confidence": 0.90
        },
        {
            "keywords": ['internet', 'wifi', 'broadband', 'data'],
            "account": '8009 - Internet expenses',
            "confidence": 0.87
        },
        {
            "keywords": ['electricity', 'power', 'nepa', 'phcn'],
            "account": '8011 - Electricity expenses',
            "confidence": 0.92
        },
        {
            "keywords": ['insurance', 'premium', 'coverage'],
            "account": '8012 - Insurance expenses',
            "confidence": 0.88
        },
        {
            "keywords": ['repair', 'maintenance', 'fixing'],
            "account": '8013 - Repairs and maintenance',
            "confidence": 0.85
        }
    ]
    
    best_match = None
    best_confidence = 0
    
    for category in categories:
        for keyword in category["keywords"]:
            if keyword in remark_lower:
                if category["confidence"] > best_confidence:
                    best_match = category["account"]
                    best_confidence = category["confidence"]
    
    if best_match and best_confidence > 0.80:
        return {
            "account": best_match,
            "confidence": best_confidence,
            "reason": "AI categorization based on remark analysis"
        }
    
    return None


@frappe.whitelist()
def get_bank_balance(bank_account, as_on_date=None):
    """
    Get bank balance as on a specific date
    
    Args:
        bank_account: Bank Account name
        as_on_date: Date for balance check (default: today)
    
    Returns:
        Dictionary with balance information
    """
    if not as_on_date:
        as_on_date = today()
    
    bank_account_doc = frappe.get_doc("Bank Account", bank_account)
    account = bank_account_doc.account
    
    balance = frappe.db.sql("""
        SELECT 
            SUM(debit) - SUM(credit) as balance
        FROM `tabGL Entry`
        WHERE account = %s 
        AND posting_date <= %s
        AND is_cancelled = 0
    """, (account, as_on_date), as_dict=1)[0]
    
    return {
        "account": account,
        "balance": flt(balance.balance) if balance else 0,
        "as_on_date": as_on_date,
        "currency": bank_account_doc.account_currency
    }


@frappe.whitelist()
def reconcile_batch(doc_name):
    """
    Reconcile batch with actual bank statement
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
    
    Returns:
        Dictionary with reconciliation status
    """
    doc = frappe.get_doc("Batch Bank Transaction", doc_name)
    
    # Get current bank balance
    bank_balance = get_bank_balance(doc.bank_account, doc.batch_date)
    
    # Calculate expected balance
    expected_balance = flt(doc.opening_balance) + flt(doc.total_inflow) - flt(doc.total_outflow)
    
    difference = expected_balance - flt(bank_balance["balance"])
    
    return {
        "status": "matched" if abs(difference) < 0.01 else "mismatch",
        "expected_balance": expected_balance,
        "actual_balance": bank_balance["balance"],
        "difference": difference,
        "currency": doc.bank_account_currency
    }


@frappe.whitelist()
def bulk_update_cost_center(doc_name, cost_center):
    """
    Bulk update cost center for all transactions
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
        cost_center: Cost Center to set
    
    Returns:
        Success message
    """
    doc = frappe.get_doc("Batch Bank Transaction", doc_name)
    
    if doc.docstatus != 0:
        frappe.throw(_("Cannot update submitted document"))
    
    for trans in doc.transaction_entry:
        trans.cost_center = cost_center
    
    doc.save()
    
    return {
        "success": True,
        "message": f"Updated {len(doc.transaction_entry)} transactions with cost center {cost_center}"
    }


@frappe.whitelist()
def generate_batch_report(doc_name):
    """
    Generate comprehensive batch report
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
    
    Returns:
        Dictionary with report data
    """
    doc = frappe.get_doc("Batch Bank Transaction", doc_name)
    
    # Transaction type breakdown
    type_breakdown = {}
    for trans in doc.transaction_entry:
        trans_type = trans.trans_type
        type_breakdown[trans_type] = type_breakdown.get(trans_type, 0) + 1
    
    # Party breakdown
    party_breakdown = {}
    for trans in doc.transaction_entry:
        if trans.party:
            if trans.party not in party_breakdown:
                party_breakdown[trans.party] = {"count": 0, "total_amount": 0}
            party_breakdown[trans.party]["count"] += 1
            party_breakdown[trans.party]["total_amount"] += flt(trans.amount)
    
    # Daily breakdown
    daily_breakdown = {}
    for trans in doc.transaction_entry:
        date = cstr(trans.posting_date)
        if date not in daily_breakdown:
            daily_breakdown[date] = {"inflow": 0, "outflow": 0, "count": 0}
        daily_breakdown[date]["inflow"] += flt(trans.inflow)
        daily_breakdown[date]["outflow"] += flt(trans.outflow)
        daily_breakdown[date]["count"] += 1
    
    return {
        "summary": {
            "total_transactions": len(doc.transaction_entry),
            "total_inflow": doc.total_inflow,
            "total_outflow": doc.total_outflow,
            "net_balance": doc.balance,
            "opening_balance": doc.opening_balance
        },
        "type_breakdown": type_breakdown,
        "party_breakdown": party_breakdown,
        "daily_breakdown": daily_breakdown
    }


# ========================================
# SCHEDULED JOBS
# ========================================

def process_recurring_transactions():
    """
    Process recurring transactions (to be run as scheduled job)
    """
    # Get all active recurring transactions
    recurring_trans = frappe.db.sql("""
        SELECT 
            parent, name, posting_date, next_posting_date, 
            charged_amount, frequency, no_of_periods
        FROM `tabTransaction Entry`
        WHERE frequency IS NOT NULL
        AND next_posting_date <= %s
        AND (end_date IS NULL OR end_date >= %s)
    """, (today(), today()), as_dict=1)
    
    for trans in recurring_trans:
        try:
            # Create new transaction entry
            create_recurring_entry(trans)
            
            # Update next posting date
            update_next_posting_date(trans)
            
        except Exception as e:
            frappe.log_error(f"Error processing recurring transaction {trans.name}: {str(e)}")


def create_recurring_entry(trans):
    """Create new entry from recurring transaction"""
    # Implementation for creating recurring entries
    pass


def update_next_posting_date(trans):
    """Update next posting date for recurring transaction"""
    # Implementation for updating next date
    pass




def validate_party_name(doc, method):
    """Validate and update party names"""
    for entry in doc.transaction_entry:
        if entry.trans_type == "Supplier Payment" and entry.party:
            entry.party_name = frappe.db.get_value('Supplier', entry.party, 'supplier_name')
        elif entry.trans_type == "Customer Receipt" and entry.party:
            entry.party_name = frappe.db.get_value('Customer', entry.party, 'customer_name')


def update_party_names(doc, method):
    """Update party names before saving"""
    for entry in doc.transaction_entry:
        if entry.party_type == "Supplier" and entry.party:
            supplier_name = frappe.db.get_value('Supplier', entry.party, 'supplier_name')
            if supplier_name:
                entry.party_name = supplier_name
                entry.payee_name = supplier_name
        
        elif entry.party_type == "Customer" and entry.party:
            customer_name = frappe.db.get_value('Customer', entry.party, 'customer_name')
            if customer_name:
                entry.party_name = customer_name
                entry.payee_name = customer_name


def on_batch_submit(doc, method):
    """Handle batch submission"""
    # Send notification to relevant users
    notify_batch_submission(doc)
    
    # Create dashboard update
    update_dashboard_metrics(doc)


def on_batch_cancel(doc, method):
    """Handle batch cancellation"""
    # Send notification
    notify_batch_cancellation(doc)


def notify_batch_submission(doc):
    """Send notification when batch is submitted"""
    # Get relevant users
    users_to_notify = get_notification_users(doc)
    
    for user in users_to_notify:
        frappe.publish_realtime(
            event='batch_submitted',
            message={
                'batch_name': doc.name,
                'bank_account': doc.bank_account,
                'total_amount': doc.total_inflow + doc.total_outflow,
                'transaction_count': len(doc.transaction_entry)
            },
            user=user
        )


def notify_batch_cancellation(doc):
    """Send notification when batch is cancelled"""
    users_to_notify = get_notification_users(doc)
    
    for user in users_to_notify:
        frappe.publish_realtime(
            event='batch_cancelled',
            message={
                'batch_name': doc.name,
                'bank_account': doc.bank_account
            },
            user=user
        )


def get_notification_users(doc):
    """Get list of users to notify"""
    users = []
    
    # Add batch owner
    if doc.batch_owner:
        users.append(doc.batch_owner)
    
    # Add users with specific roles
    accounts_managers = frappe.get_all("Has Role",
        filters={"role": "Accounts Manager", "parenttype": "User"},
        fields=["parent"])
    
    users.extend([u.parent for u in accounts_managers])
    
    return list(set(users))  # Remove duplicates


def update_dashboard_metrics(doc):
    """Update dashboard metrics after batch submission"""
    # This can be used to update custom dashboards
    pass


def send_batch_reminders():
    """Send reminders for pending batches (scheduled hourly)"""
    # Get draft batches older than 24 hours
    pending_batches = frappe.get_all("Batch Bank Transaction",
        filters={
            "docstatus": 0,
            "creation": ["<", frappe.utils.add_to_date(today(), hours=-24)]
        },
        fields=["name", "batch_owner", "bank_account"])
    
    for batch in pending_batches:
        if batch.batch_owner:
            # Send email reminder
            frappe.sendmail(
                recipients=[batch.batch_owner],
                subject=f"Reminder: Pending Batch Bank Transaction - {batch.name}",
                message=f"""
                    <p>Dear User,</p>
                    <p>You have a pending Batch Bank Transaction that has not been submitted:</p>
                    <ul>
                        <li><strong>Batch:</strong> {batch.name}</li>
                        <li><strong>Bank Account:</strong> {batch.bank_account}</li>
                    </ul>
                    <p>Please review and submit the batch at your earliest convenience.</p>
                """,
                reference_doctype="Batch Bank Transaction",
                reference_name=batch.name
            )