import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    flt, getdate, add_months, money_in_words, today, date_diff, 
    add_days, nowdate, fmt_money, get_url
)
from frappe.utils.pdf import get_pdf
from frappe.utils.print_format import download_pdf
import json


class Receipts(Document):
    """Main Receipt Document Class"""
    
    def validate(self):
        """Validate document before saving"""
        # Basic validations
        self.validate_required_fields()
        self.validate_dates()
        self.validate_amounts()
        self.validate_bank_account()
        
        # Calculate local currency amount in real-time
        self.calculate_local_currency_amount()
        
        # Calculate totals for multi-line
        if self.is_multi_line and self.receipts_item_line:
            self.validate_multi_line_items()
            self.total = sum(flt(row.amount) for row in self.receipts_item_line)
        
        # Calculate totals for related company
        if self.is_related_coy_trans and self.related_company_receipts:
            self.total_rcoy = sum(flt(row.amount) for row in self.related_company_receipts)
        
        # Calculate total outstanding invoices
        if self.receipts_reference:
            self.validate_customer_invoice_allocation()
            self.total_outstanding_invoice = sum(flt(row.allocated_amount) for row in self.receipts_reference)
        
        # Populate party names for related companies
        self.populate_related_party_names()
        
        # Business validations
        self.validate_duplicate_receipt()
        self.validate_unallocated_amount()
    
    def validate_required_fields(self):
        """Validate that required fields are populated"""
        # Check transaction type
        if not self.trans_type:
            frappe.throw(_("Please select a Transaction Type"))
        
        # Check company
        if not self.company:
            frappe.throw(_("Please select a Company"))
        
        # Check receipt currency
        if not self.receipt_currency:
            frappe.throw(_("Please select Receipt Currency"))
        
        # Check remittance bank for accounting entries
        if self.create_accounting_entries and not self.remittance_bank:
            frappe.throw(_("Remittance Bank is required for creating accounting entries"))
        
        # Check remittance bank GL
        if self.create_accounting_entries and not self.remittance_bank_gl:
            frappe.throw(_("Remittance Bank GL is required for creating accounting entries"))
        
        # Validate customer for customer receipts
        if self.trans_type in ["Customer Receipt", "Receive from One-Off"] and not self.customer_id:
            frappe.throw(_("Customer is required for Customer Receipt transactions"))
        
        # Validate payer name for non-customer receipts
        if self.trans_type not in ["Customer Receipt", "Customer Refund"] and not self.payer_name:
            frappe.throw(_("Payer Name is required for {0}").format(self.trans_type))
        
        # Validate account to credit for non-customer receipts (only if not multi-line)
        if self.trans_type not in ["Customer Receipt", "Customer Refund"] and not self.is_multi_line and not self.account_to_credit:
            frappe.throw(_("Account to Credit is required for {0}").format(self.trans_type))
    
    def validate_dates(self):
        """Validate date fields"""
        if not self.transaction_date:
            frappe.throw(_("Transaction Date is mandatory"))
        
        # Transaction date cannot be in future
        if getdate(self.transaction_date) > getdate(nowdate()):
            frappe.throw(_("Transaction Date cannot be in the future"))
        
        # Validate amortization dates
        if self.amortize:
            if not self.start_date or not self.end_date:
                frappe.throw(_("Start Date and End Date are mandatory for amortization"))
            
            if getdate(self.end_date) <= getdate(self.start_date):
                frappe.throw(_("End Date must be after Start Date"))
    
    def validate_amounts(self):
        """Validate amount fields"""
        if not self.company:
            frappe.throw(_("Company is required"))
            
        company_currency = frappe.db.get_value('Company', self.company, 'default_currency')
        
        if not company_currency:
            frappe.throw(_("Company currency not found for {0}").format(self.company))
        
        if self.receipt_currency == company_currency:
            if not self.amount_received or self.amount_received <= 0:
                frappe.throw(_("Amount Received must be greater than zero"))
        else:
            if not self.amount_received_in_fc or self.amount_received_in_fc <= 0:
                frappe.throw(_("Amount Received in Foreign Currency must be greater than zero"))
            
            if not self.exchange_rate or self.exchange_rate <= 0:
                frappe.throw(_("Exchange Rate must be greater than zero"))
    
    def validate_bank_account(self):
        """Validate bank account"""
        if not self.remittance_bank:
            return
        
        # Check if bank account exists and get account currency
        bank = frappe.db.get_value('Bank Account', self.remittance_bank, 
            ['account', 'account_currency'], as_dict=1)
        
        if not bank:
            frappe.throw(_("Bank Account {0} not found").format(self.remittance_bank))
        
        # Validate bank account currency matches receipt currency for foreign currency
        if not self.company:
            return
            
        company_currency = frappe.db.get_value('Company', self.company, 'default_currency')
        if self.receipt_currency != company_currency:
            if bank.account_currency and bank.account_currency != self.receipt_currency:
                frappe.msgprint(_("Warning: Bank account currency ({0}) does not match receipt currency ({1})").format(
                    bank.account_currency, self.receipt_currency
                ), alert=True, indicator='orange')
    
    def validate_customer_invoice_allocation(self):
        """Validate customer invoice allocation"""
        if self.trans_type != "Customer Receipt":
            return
        
        if not self.receipts_reference:
            return
        
        total_allocated = sum([flt(row.allocated_amount) for row in self.receipts_reference])
        receipt_amount = self.amount_received or self.amount_received_in_fc or 0
        
        # Warning if over-allocated
        if total_allocated > receipt_amount:
            frappe.throw(_("Total allocated amount {0} {1:,.2f} cannot exceed receipt amount {2} {3:,.2f}").format(
                self.receipt_currency, total_allocated,
                self.receipt_currency, receipt_amount
            ))
        
        # Validate each allocation
        for row in self.receipts_reference:
            if flt(row.allocated_amount) > flt(row.outstanding_amount):
                frappe.throw(_("Row {0}: Allocated amount cannot exceed outstanding amount").format(row.idx))
            
            if flt(row.allocated_amount) < 0:
                frappe.throw(_("Row {0}: Allocated amount cannot be negative").format(row.idx))
    
    def validate_multi_line_items(self):
        """Validate multi-line items"""
        if not self.is_multi_line:
            return
        
        if not self.receipts_item_line:
            frappe.throw(_("Please add line items for multi-line receipt"))
        
        total = sum([flt(row.amount) for row in self.receipts_item_line])
        receipt_amount = self.local_currency_amount or self.amount_received or 0
        
        # Validate individual rows
        for row in self.receipts_item_line:
            if not row.gl_account:
                frappe.throw(_("Row {0}: GL Account is mandatory").format(row.idx))
            
            if not row.amount or row.amount <= 0:
                frappe.throw(_("Row {0}: Amount must be greater than zero").format(row.idx))
        
        # Check if totals match (with tolerance)
        if abs(total - receipt_amount) > 0.01:
            frappe.msgprint(_("Warning: Multi-line total ({0}) does not match receipt amount ({1})").format(
                total, receipt_amount
            ), alert=True, indicator='orange')
    
    def validate_duplicate_receipt(self):
        """Check for potential duplicate receipts"""
        if not self.customer_id or not self.amount_received:
            return
        
        if not self.transaction_date:
            return
        
        # Check for similar receipts in last 7 days
        from_date = add_days(self.transaction_date, -7)
        
        similar_receipts = frappe.db.sql("""
            SELECT name, transaction_date, amount_received, reference_no
            FROM `tabReceipts`
            WHERE 
                customer_id = %(customer)s
                AND ABS(amount_received - %(amount)s) < 0.01
                AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
                AND docstatus != 2
                AND name != %(current)s
        """, {
            'customer': self.customer_id,
            'amount': self.amount_received,
            'from_date': from_date,
            'to_date': self.transaction_date,
            'current': self.name or 'new'
        }, as_dict=1)
        
        if similar_receipts:
            receipt_list = ', '.join([r.name for r in similar_receipts])
            frappe.msgprint(_("Warning: Similar receipt(s) found in the last 7 days: {0}").format(receipt_list),
                alert=True, indicator='orange')
    
    def validate_unallocated_amount(self):
        """Warn if there's unallocated amount"""
        if self.trans_type != "Customer Receipt":
            return
        
        if not self.receipts_reference:
            # No allocations at all
            frappe.msgprint(_("Info: Receipt amount is not allocated to any invoice. This will create a credit balance."),
                alert=True, indicator='blue')
            return
        
        total_allocated = sum([flt(row.allocated_amount) for row in self.receipts_reference])
        receipt_amount = self.amount_received or self.amount_received_in_fc or 0
        unallocated = receipt_amount - total_allocated
        
        if unallocated > 0.01:
            frappe.msgprint(_("Info: Unallocated amount of {0} will remain as customer credit balance").format(
                frappe.format_value(unallocated, {'fieldtype': 'Currency', 'currency': self.receipt_currency})
            ), alert=True, indicator='blue')
    
    def validate_unique_reference(self):
        """Check if reference number is unique"""
        if not self.reference_no:
            return
        
        filters = {
            'reference_no': self.reference_no,
            'docstatus': ['!=', 2],
            'name': ['!=', self.name]
        }
        
        exists = frappe.db.exists('Receipts', filters)
        
        if exists:
            frappe.throw(_("Reference number {0} already exists in Receipt {1}").format(
                self.reference_no, exists
            ))
    
    def calculate_local_currency_amount(self):
        """Calculate local currency amount in real-time"""
        if not self.company:
            return
            
        company_currency = frappe.db.get_value('Company', self.company, 'default_currency')
        
        if not company_currency:
            return
        
        if self.receipt_currency == company_currency:
            self.local_currency_amount = self.amount_received or 0
        else:
            exchange_rate = self.exchange_rate or 1
            amount_fc = self.amount_received_in_fc or 0
            self.local_currency_amount = amount_fc * exchange_rate
    
    def populate_related_party_names(self):
        """Populate party names for related company transactions"""
        for row in self.related_company_receipts or []:
            if row.party_type and row.party:
                try:
                    doctype = "Supplier" if row.party_type == "Supplier" else "Customer"
                    field_name = "supplier_name" if row.party_type == "Supplier" else "customer_name"
                    party_name = frappe.db.get_value(doctype, row.party, field_name)
                    if party_name:
                        row.party_name = party_name
                except Exception as e:
                    frappe.log_error(f"Error fetching party name: {str(e)}", "Party Name Error")
    
    def before_submit(self):
        """Before submitting receipt"""
        # Validate again before submit
        self.validate_required_fields()
        self.validate_unique_reference()
        
        # Set amount in words
        if self.amount_received and self.amount_received > 0:
            amount = self.amount_received
        else:
            amount = self.amount_received_in_fc if self.amount_received_in_fc else 0
        
        if amount > 0:
            amount_words = money_in_words(amount, self.receipt_currency)
            if not amount_words.upper().startswith(self.receipt_currency.upper()):
                amount_words = f"{self.receipt_currency} {amount_words}"
            self.amount_in_words = amount_words
        
        # Set title
        self.title = self.customer_name if self.customer_name else self.payer_name
        
        # Set approval fields
        self.issued_by = frappe.session.user
        self.date = self.transaction_date or today()
        self.auth_date = today()
        self.authorised_by = frappe.session.user
        
        # Calculate local currency amount
        self.calculate_local_currency_amount()
        
        # Log submission attempt
        frappe.logger().info(f"Submitting Receipt {self.name} - Trans Type: {self.trans_type}, Create Entries: {self.create_accounting_entries}")
    
    def on_submit(self):
        """After submitting receipt"""
        frappe.logger().info(f"Receipt {self.name} submitted - Starting accounting entry creation")
        
        if not self.create_accounting_entries:
            frappe.msgprint(_("Accounting entry creation is disabled"), indicator="blue")
            return
        
        creator = ReceiptEntryCreator(self)
        
        # Validate no duplicates
        try:
            creator.validate_duplicate_entries()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Duplicate Entry Validation Error")
            frappe.throw(_("Duplicate entry validation failed: {0}").format(str(e)))
        
        try:
            created_entries = []
            
            # Create appropriate entries based on transaction type
            if self.trans_type in ["Customer Receipt", "Receive from One-Off"]:
                frappe.logger().info(f"Creating Payment Entry for {self.trans_type}")
                entry = creator.create_customer_payment_entry()
                if entry:
                    created_entries.append({"type": "Payment Entry", "name": entry})
            
            elif self.trans_type == "Revenue Receipt":
                frappe.logger().info(f"Creating Revenue Receipt Entry - Multi-line: {self.is_multi_line}")
                # For multi-line, create only ONE journal entry
                if self.is_multi_line:
                    entry = creator.create_multi_line_journal()
                    if entry:
                        created_entries.append({"type": "Journal Entry", "name": entry})
                else:
                    entry = creator.create_revenue_receipt_journal()
                    if entry:
                        created_entries.append({"type": "Journal Entry", "name": entry})
                
                # Create amortization journals if applicable
                amort_entries = creator.create_amortization_journals()
                for entry in amort_entries:
                    created_entries.append({"type": "Amortization Journal", "name": entry})
            
            elif self.trans_type == "Transfer In":
                frappe.logger().info(f"Creating Transfer In Entry")
                entry = creator.create_transfer_in_journal()
                if entry:
                    created_entries.append({"type": "Journal Entry", "name": entry})
            
            # Handle related company transactions
            if self.is_related_coy_trans:
                frappe.logger().info(f"Creating Related Company Entries")
                rel_entries = creator.create_related_company_entries()
                for entry in rel_entries:
                    created_entries.append({"type": "Related Company Entry", "name": entry})
            
            frappe.db.commit()
            
            # Log created entries
            if created_entries:
                entry_list = ", ".join([f"{e['type']}: {e['name']}" for e in created_entries])
                frappe.msgprint(_("Accounting entries created successfully: {0}").format(entry_list), 
                              indicator="green", 
                              title="Success")
                frappe.logger().info(f"Created entries: {entry_list}")
            else:
                frappe.msgprint(_("No accounting entries were created. Please check transaction type and settings."), 
                              indicator="orange",
                              title="Warning")
                frappe.logger().warning(f"No entries created for {self.name}")
            
            # Send email confirmation asynchronously
            frappe.enqueue(
                method='ecclesia.ecclesia.doctype.receipts.receipts.send_customer_email_async',
                queue='short',
                timeout=300,
                is_async=True,
                receipt_name=self.name
            )
            
        except Exception as e:
            frappe.db.rollback()
            error_msg = str(e)
            frappe.log_error(frappe.get_traceback(), "Receipt Entry Creation Error")
            frappe.throw(_("Error creating accounting entries: {0}").format(error_msg))
    
    def on_cancel(self):
        """After cancelling receipt"""
        # Check for linked documents
        self.validate_before_cancel()
        
        # Cancel related entries
        cancel_related_entries(self)
        frappe.msgprint(_("Related accounting entries cancelled"), indicator="orange")
    
    def validate_before_cancel(self):
        """Validations before cancellation"""
        # Check if there are any linked documents
        linked_docs = self.get_linked_documents()
        
        if linked_docs:
            msg = _("The following accounting entries will be cancelled:")
            for doctype, docs in linked_docs.items():
                msg += f"\n{doctype}: {', '.join(docs)}"
            frappe.msgprint(msg, alert=True, indicator='orange')
    
    def get_linked_documents(self):
        """Get linked documents"""
        linked = {}
        
        # Check for Journal Entries
        je_list = frappe.get_all('Journal Entry',
            filters={
                'cheque_no': self.reference_no,
                'docstatus': 1
            },
            pluck='name')
        
        if je_list:
            linked['Journal Entry'] = je_list
        
        # Check for Payment Entries
        pe_list = frappe.get_all('Payment Entry',
            filters={
                'reference_no': self.reference_no,
                'docstatus': 1
            },
            pluck='name')
        
        if pe_list:
            linked['Payment Entry'] = pe_list
        
        return linked
    
    def send_customer_email(self):
        """Send receipt confirmation email to customer"""
        if not self.customer_id:
            return
        
        try:
            # Get customer email
            customer = frappe.get_doc("Customer", self.customer_id)
            if not customer.email_id:
                return
            
            # Get print format
            print_format = frappe.db.get_single_value("Accounts Settings", "default_receipt_print_format") or "Standard"
            
            # Generate PDF
            pdf_content = frappe.attach_print(
                doctype=self.doctype,
                name=self.name,
                print_format=print_format,
                doc=self
            )
            
            # Email content
            subject = _("Payment Receipt - {0}").format(self.name)
            message = f"""
            <p>Dear {self.customer_name},</p>
            
            <p>Thank you for your payment. Please find attached your official receipt for the payment received.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Receipt No:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self.name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Date:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self.transaction_date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Amount Received:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self.amount_in_words}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Reference No:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self.reference_no}</td>
                </tr>
            </table>
            
            <p>If you have any questions, please don't hesitate to contact us.</p>
            
            <p>Best regards,<br>
            {self.company}</p>
            """
            
            # Send email
            frappe.sendmail(
                recipients=[customer.email_id],
                subject=subject,
                message=message,
                attachments=[{
                    'fname': f"{self.name}.pdf",
                    'fcontent': pdf_content
                }],
                reference_doctype=self.doctype,
                reference_name=self.name
            )
            
            frappe.logger().info(f"Receipt confirmation email sent to {customer.email_id}")
            
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Receipt Customer Email Error")
            # Don't throw error, just log it


class ReceiptEntryCreator:
    """Handles creation of accounting entries for Receipt documents"""
    
    def __init__(self, doc):
        self.doc = doc
        
        if not doc.company:
            frappe.throw(_("Company is required"))
            
        self.company_doc = frappe.get_doc("Company", doc.company)
        self.company_currency = self.company_doc.default_currency
        self.is_local_currency = doc.receipt_currency == self.company_currency
        
        frappe.logger().info(f"ReceiptEntryCreator initialized - Currency: {doc.receipt_currency}, Is Local: {self.is_local_currency}")
        
    def validate_duplicate_entries(self):
        """Prevent duplicate journal/payment entries"""
        if not self.doc.reference_no:
            frappe.logger().warning("No reference number provided for duplicate check")
            return
            
        existing_je = frappe.db.exists("Journal Entry", {
            "cheque_no": self.doc.reference_no,
            "docstatus": ["<", 2]  # Draft or Submitted
        })
        if existing_je:
            frappe.throw(_("Journal Entry with Reference No '{0}' already exists: {1}").format(
                self.doc.reference_no, existing_je))
        
        existing_pe = frappe.db.exists("Payment Entry", {
            "reference_no": self.doc.reference_no,
            "docstatus": ["<", 2]  # Draft or Submitted
        })
        if existing_pe:
            frappe.throw(_("Payment Entry with Reference No '{0}' already exists: {1}").format(
                self.doc.reference_no, existing_pe))
    
    def validate_account_not_group(self, account):
        """Ensure account is not a group account"""
        if not account:
            return
        is_group = frappe.db.get_value("Account", account, "is_group")
        if is_group:
            frappe.throw(_("The account {0} is a group account and cannot be used for posting transactions").format(account))
    
    def create_customer_payment_entry(self):
        """Create Payment Entry for Customer Receipts"""
        frappe.logger().info(f"Starting create_customer_payment_entry for {self.doc.name}")
        
        if self.doc.trans_type not in ["Customer Receipt", "Receive from One-Off"]:
            frappe.logger().info(f"Skipping - trans_type is {self.doc.trans_type}")
            return None
            
        if not self.doc.create_accounting_entries:
            frappe.logger().info("Skipping - create_accounting_entries is False")
            return None
        
        try:
            payment_entry = frappe.new_doc("Payment Entry")
            payment_entry.party_type = "Customer"
            payment_entry.party = self.doc.customer_id
            payment_entry.payment_type = "Receive"
            payment_entry.mode_of_payment = self.doc.mode_of_payment
            payment_entry.company = self.doc.company
            payment_entry.paid_to = self.doc.remittance_bank_gl
            payment_entry.paid_from = self.company_doc.default_receivable_account
            payment_entry.bank_account = self.doc.remittance_bank
            payment_entry.posting_date = self.doc.transaction_date
            payment_entry.reference_no = self.doc.reference_no
            payment_entry.reference_date = self.doc.transaction_date
            payment_entry.remarks = self.doc.transaction_purposes or f"Receipt from {self.doc.customer_name}"
            
            # Handle currency amounts
            if self.is_local_currency:
                payment_entry.paid_amount = self.doc.amount_received
                payment_entry.received_amount = self.doc.amount_received
                payment_entry.source_exchange_rate = 1
                payment_entry.target_exchange_rate = 1
            else:
                payment_entry.paid_amount = self.doc.amount_received_in_fc * self.doc.exchange_rate
                payment_entry.received_amount = self.doc.amount_received_in_fc
                payment_entry.paid_to_account_currency = self.doc.bank_account_currency
                payment_entry.source_exchange_rate = 1
                payment_entry.target_exchange_rate = self.doc.exchange_rate
            
            # Add invoice references with proper error handling
            if self.doc.get("receipts_reference"):
                for ref in self.doc.receipts_reference:
                    if ref.allocated_amount and ref.allocated_amount > 0:
                        payment_entry.append("references", {
                            "reference_doctype": ref.reference_doctype or "Sales Invoice",
                            "reference_name": ref.reference_name,
                            "due_date": ref.due_date,
                            "bill_no": ref.bill_no,
                            "payment_term": ref.payment_term or "",
                            "total_amount": ref.total_amount,
                            "outstanding_amount": ref.outstanding_amount,
                            "allocated_amount": ref.allocated_amount,
                            "exchange_rate": ref.exchange_rate or 1,
                            "exchange_gain_loss": ref.exchange_gain_loss or 0
                        })
            
            payment_entry.flags.ignore_mandatory = True
            payment_entry.flags.ignore_permissions = True
            payment_entry.insert(ignore_permissions=True)
            payment_entry.submit()
            
            frappe.logger().info(f"Payment Entry {payment_entry.name} created and submitted")
            frappe.msgprint(_("Payment Entry {0} created").format(payment_entry.name), indicator="green")
            return payment_entry.name
            
        except Exception as e:
            frappe.logger().error(f"Error creating payment entry: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Payment Entry Creation Error")
            raise
    
    def create_revenue_receipt_journal(self):
        """Create Journal Entry for Revenue Receipts (non-multi-line)"""
        frappe.logger().info(f"Starting create_revenue_receipt_journal for {self.doc.name}")
        
        if self.doc.trans_type != "Revenue Receipt":
            frappe.logger().info(f"Skipping - trans_type is {self.doc.trans_type}")
            return None
            
        if not self.doc.create_accounting_entries:
            frappe.logger().info("Skipping - create_accounting_entries is False")
            return None
        
        if self.doc.is_multi_line:
            frappe.logger().info("Skipping - is_multi_line is True")
            return None  # Multi-line has its own method
        
        try:
            self.validate_account_not_group(self.doc.account_to_credit)
            
            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.voucher_type = "Bank Entry"
            journal_entry.naming_series = "BJV-.#####"
            journal_entry.paid_to_or_received_from = self.doc.payer_name
            journal_entry.company = self.doc.company
            journal_entry.custom_bank_account = self.doc.remittance_bank
            journal_entry.trans_type = "Receive"
            journal_entry.transaction_description = self.doc.transaction_purposes
            journal_entry.posting_date = self.doc.transaction_date
            journal_entry.user_remark = self.doc.transaction_purposes
            journal_entry.reference_document_no = self.doc.name
            journal_entry.cheque_no = self.doc.reference_no
            journal_entry.cheque_date = self.doc.transaction_date
            journal_entry.multi_currency = 0 if self.is_local_currency else 1
            
            # Debit: Bank Account
            debit_amount = self.doc.amount_received if self.is_local_currency else self.doc.amount_received_in_fc
            journal_entry.append("accounts", {
                "account": self.doc.remittance_bank_gl,
                "bank_account": self.doc.remittance_bank,
                "debit_in_account_currency": debit_amount,
                "debit": debit_amount * self.doc.exchange_rate if not self.is_local_currency else debit_amount,
                "exchange_rate": self.doc.exchange_rate if not self.is_local_currency else 1,
                "user_remark": self.doc.transaction_purposes,
                "against_account": self.doc.account_to_credit
            })
            
            # Credit: Revenue/Deferred Revenue Account
            credit_amount = self.doc.amount_received if self.is_local_currency else self.doc.amount_received_in_fc * self.doc.exchange_rate
            journal_entry.append("accounts", {
                "account": self.doc.account_to_credit,
                "credit_in_account_currency": credit_amount,
                "credit": credit_amount,
                "user_remark": self.doc.transaction_purposes,
                "cost_center": self.doc.cost_center,
                "exchange_rate": 1,
                "account_currency": self.company_currency,
                "against_account": self.doc.remittance_bank_gl
            })
            
            journal_entry.set_total_debit_credit()
            journal_entry.flags.ignore_permissions = True
            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()
            
            frappe.logger().info(f"Journal Entry {journal_entry.name} created and submitted")
            frappe.msgprint(_("Journal Entry {0} created").format(journal_entry.name), indicator="green")
            return journal_entry.name
            
        except Exception as e:
            frappe.logger().error(f"Error creating revenue journal: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Revenue Journal Creation Error")
            raise
    
    def create_multi_line_journal(self):
        """Create ONE journal entry for multi-line transactions"""
        frappe.logger().info(f"Starting create_multi_line_journal for {self.doc.name}")
        
        if not (self.doc.is_multi_line and self.doc.receipts_item_line):
            frappe.logger().info("Skipping - not multi-line or no line items")
            return None
        
        try:
            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.voucher_type = "Bank Entry"
            journal_entry.naming_series = "BJV-.#####"
            journal_entry.posting_date = self.doc.transaction_date
            journal_entry.reference_document_no = self.doc.name
            journal_entry.cheque_no = self.doc.reference_no
            journal_entry.cheque_date = self.doc.transaction_date
            journal_entry.company = self.doc.company
            journal_entry.paid_to_or_received_from = self.doc.payer_name
            journal_entry.custom_bank_account = self.doc.remittance_bank
            journal_entry.transaction_description = self.doc.transaction_purposes
            journal_entry.multi_currency = 0 if self.is_local_currency else 1
            
            # Credit entries for each line item (multiple credits)
            for row in self.doc.receipts_item_line:
                if row.gl_account and row.amount:
                    self.validate_account_not_group(row.gl_account)
                    amount = row.amount if self.is_local_currency else row.amount * (row.exch_rate or 1)
                    
                    journal_entry.append('accounts', {
                        'account': row.gl_account,
                        'credit_in_account_currency': amount,
                        'credit': amount,
                        'exchange_rate': row.exch_rate if not self.is_local_currency else 1,
                        'user_remark': row.description or self.doc.transaction_purposes,
                        'cost_center': row.cost_center,
                        'against_account': self.doc.remittance_bank_gl
                    })
            
            # Debit: Bank Account (single debit)
            debit_amount = self.doc.amount_received if self.is_local_currency else self.doc.amount_received_in_fc
            against_accounts = ",".join([row.gl_account for row in self.doc.receipts_item_line if row.gl_account])
            
            journal_entry.append('accounts', {
                'account': self.doc.remittance_bank_gl,
                'debit_in_account_currency': debit_amount,
                'debit': debit_amount * self.doc.exchange_rate if not self.is_local_currency else debit_amount,
                'exchange_rate': self.doc.exchange_rate if not self.is_local_currency else 1,
                'bank_account': self.doc.remittance_bank,
                'user_remark': self.doc.transaction_purposes,
                'against_account': against_accounts
            })
            
            journal_entry.set_total_debit_credit()
            journal_entry.flags.ignore_permissions = True
            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()
            
            frappe.logger().info(f"Multi-line Journal Entry {journal_entry.name} created and submitted")
            frappe.msgprint(_("Multi-line Journal Entry {0} created").format(journal_entry.name), indicator="green")
            return journal_entry.name
            
        except Exception as e:
            frappe.logger().error(f"Error creating multi-line journal: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Multi-line Journal Creation Error")
            raise
    
    def create_amortization_journals(self):
        """Create periodic amortization journal entries"""
        frappe.logger().info(f"Starting create_amortization_journals for {self.doc.name}")
        
        if not (self.doc.trans_type == "Revenue Receipt" and 
                self.doc.create_accounting_entries and 
                self.doc.amortize and 
                self.doc.frequency in ["Monthly", "Quarterly"]):
            frappe.logger().info("Skipping - conditions not met for amortization")
            return []
        
        try:
            self.validate_account_not_group(self.doc.deferred_revenue_account)
            self.validate_account_not_group(self.doc.revenue_account)
            
            period_months = 1 if self.doc.frequency == "Monthly" else 3
            no_of_periods = int(date_diff(self.doc.end_date, self.doc.start_date) / (30 * period_months))
            
            created_entries = []
            
            for i in range(1, no_of_periods + 1):
                posting_date = add_months(self.doc.start_date, (i - 1) * period_months)
                posting_date = getdate(posting_date)
                
                if posting_date > getdate(self.doc.end_date):
                    break
                
                journal_entry = frappe.new_doc("Journal Entry")
                journal_entry.voucher_type = "Deferred Revenue"
                journal_entry.naming_series = "IRJ-JRN-.#####"
                journal_entry.paid_to_or_received_from = self.doc.payer_name
                journal_entry.company = self.doc.company
                journal_entry.transaction_description = self.doc.transaction_purposes
                journal_entry.posting_date = posting_date
                journal_entry.user_remark = self.doc.transaction_purposes
                journal_entry.reference_document_no = self.doc.name
                journal_entry.cheque_no = self.doc.reference_no
                journal_entry.cheque_date = posting_date
                
                # Debit: Deferred Revenue
                journal_entry.append("accounts", {
                    "account": self.doc.deferred_revenue_account,
                    "debit_in_account_currency": self.doc.charge_amount,
                    "user_remark": self.doc.transaction_purposes,
                    "against_account": self.doc.revenue_account
                })
                
                # Credit: Revenue
                journal_entry.append("accounts", {
                    "account": self.doc.revenue_account,
                    "credit_in_account_currency": self.doc.charge_amount,
                    "user_remark": self.doc.transaction_purposes,
                    "cost_center": self.doc.cost_center,
                    "against_account": self.doc.deferred_revenue_account
                })
                
                journal_entry.set_total_debit_credit()
                journal_entry.flags.ignore_permissions = True
                journal_entry.insert(ignore_permissions=True)
                journal_entry.submit()
                
                created_entries.append(journal_entry.name)
            
            if created_entries:
                frappe.logger().info(f"Created {len(created_entries)} amortization entries")
                frappe.msgprint(_("Created {0} amortization entries").format(len(created_entries)), indicator="green")
            
            return created_entries
            
        except Exception as e:
            frappe.logger().error(f"Error creating amortization journals: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Amortization Journal Creation Error")
            raise
    
    def create_transfer_in_journal(self):
        """Create Journal Entry for Transfer In transactions"""
        frappe.logger().info(f"Starting create_transfer_in_journal for {self.doc.name}")
        
        if self.doc.trans_type != "Transfer In":
            frappe.logger().info(f"Skipping - trans_type is {self.doc.trans_type}")
            return None
            
        if not self.doc.create_accounting_entries:
            frappe.logger().info("Skipping - create_accounting_entries is False")
            return None
        
        try:
            self.validate_account_not_group(self.doc.account_to_credit)
            
            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.voucher_type = "Bank Entry"
            journal_entry.naming_series = "BJV-.#####"
            journal_entry.custom_bank_account = self.doc.remittance_bank
            journal_entry.trans_type = "Receive"
            journal_entry.paid_to_or_received_from = self.doc.payer_name
            journal_entry.transaction_description = self.doc.transaction_purposes
            journal_entry.posting_date = self.doc.transaction_date
            journal_entry.multi_currency = 0 if self.is_local_currency else 1
            journal_entry.user_remark = self.doc.transaction_purposes
            journal_entry.reference_document_no = self.doc.name
            journal_entry.company = self.doc.company
            journal_entry.cheque_no = self.doc.reference_no
            journal_entry.cheque_date = self.doc.transaction_date
            
            # Debit: Bank Account
            if self.is_local_currency:
                debit_amount = self.doc.amount_received
                debit_amount_company = debit_amount
            else:
                debit_amount = self.doc.amount_received_in_fc
                debit_amount_company = debit_amount * self.doc.exchange_rate
            
            journal_entry.append("accounts", {
                "account": self.doc.remittance_bank_gl,
                "bank_account": self.doc.remittance_bank,
                "debit_in_account_currency": debit_amount,
                "debit": debit_amount_company,
                "user_remark": self.doc.transaction_purposes,
                "account_currency": self.doc.receipt_currency,
                "exchange_rate": self.doc.exchange_rate if not self.is_local_currency else 1,
                "against_account": self.doc.account_to_credit
            })
            
            # Credit: Transfer Account
            journal_entry.append("accounts", {
                "account": self.doc.account_to_credit,
                "exchange_rate": 1,
                "account_currency": self.company_currency,
                "credit_in_account_currency": debit_amount_company,
                "credit": debit_amount_company,
                "user_remark": self.doc.transaction_purposes,
                "against_account": self.doc.remittance_bank_gl
            })
            
            journal_entry.set_total_debit_credit()
            journal_entry.flags.ignore_permissions = True
            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()
            
            frappe.logger().info(f"Transfer Journal Entry {journal_entry.name} created and submitted")
            frappe.msgprint(_("Transfer Journal Entry {0} created").format(journal_entry.name), indicator="green")
            return journal_entry.name
            
        except Exception as e:
            frappe.logger().error(f"Error creating transfer journal: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Transfer Journal Creation Error")
            raise
    
    def create_related_company_entries(self):
        """Create entries for related company transactions"""
        frappe.logger().info(f"Starting create_related_company_entries for {self.doc.name}")
        
        if not (self.doc.is_related_coy_trans and self.doc.related_company_receipts):
            frappe.logger().info("Skipping - no related company transactions")
            return []
        
        created_entries = []
        
        for row in self.doc.related_company_receipts:
            if not (row.party and row.amount and hasattr(row, 'related_company')):
                continue
            
            try:
                # Get the related company from the row
                related_company = row.related_company
                
                # Entry 1: Journal Entry in the company making the transaction (self.doc.company)
                je_main = self.create_main_company_journal(row, related_company)
                if je_main:
                    created_entries.append(je_main)
                
                # Entry 2: Payment Entry or Journal Entry for the real owner
                if row.trans_type == "Customer Receipt":
                    pe_owner = self.create_owner_payment_entry(row, related_company)
                    if pe_owner:
                        created_entries.append(pe_owner)
                else:
                    je_owner = self.create_owner_journal_entry(row, related_company)
                    if je_owner:
                        created_entries.append(je_owner)
                        
            except Exception as e:
                frappe.logger().error(f"Error creating related company entry for row: {str(e)}")
                frappe.log_error(frappe.get_traceback(), "Related Company Entry Error")
                # Continue with other rows instead of failing completely
        
        if created_entries:
            frappe.logger().info(f"Created {len(created_entries)} related company entries")
            frappe.msgprint(_("Created {0} related company entries").format(len(created_entries)), indicator="green")
        
        return created_entries
    
    def create_main_company_journal(self, row, related_company):
        """Create journal entry in the company making the transaction"""
        transaction_purpose = f"{row.remark or 'Receipt'} for {related_company}"
        
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.naming_series = "BJV-.#####"
        journal_entry.paid_to_or_received_from = row.party_name or row.party
        journal_entry.transaction_description = transaction_purpose
        journal_entry.posting_date = self.doc.transaction_date
        journal_entry.reference_document_no = self.doc.name
        journal_entry.cheque_no = self.doc.reference_no
        journal_entry.cheque_date = self.doc.transaction_date
        journal_entry.company = self.doc.company  # Main company making transaction
        journal_entry.voucher_type = "Journal Entry"
        journal_entry.user_remark = transaction_purpose
        
        exch_rate = row.exch_rate if hasattr(row, 'exch_rate') else 1
        amount = row.amount * exch_rate
        
        # Debit: Inter-company Receivable
        intercompany_account = frappe.db.get_value('Company', self.doc.company, 'custom_intercompany_receivable_account')
        if not intercompany_account:
            intercompany_account = self.company_doc.default_receivable_account
        
        journal_entry.append("accounts", {
            "account": intercompany_account,
            "debit_in_account_currency": amount,
            "debit": amount,
            "party_type": "Company",
            "party": related_company,
            "user_remark": transaction_purpose,
            "against_account": self.doc.remittance_bank_gl
        })
        
        # Credit: Bank Account
        journal_entry.append("accounts", {
            "account": self.doc.remittance_bank_gl,
            "bank_account": self.doc.remittance_bank,
            "credit_in_account_currency": amount,
            "credit": amount,
            "user_remark": transaction_purpose,
            "against_account": intercompany_account
        })
        
        journal_entry.set_total_debit_credit()
        journal_entry.flags.ignore_permissions = True
        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()
        
        return journal_entry.name
    
    def create_owner_payment_entry(self, row, related_company):
        """Create payment entry for the real owner (Customer Receipt)"""
        if not row.party:
            return
        
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.party_type = "Customer"
        payment_entry.party = row.party
        payment_entry.payment_type = "Receive"
        payment_entry.mode_of_payment = self.doc.mode_of_payment
        payment_entry.company = related_company  # Owner company
        
        # Get accounts for owner company
        owner_company_doc = frappe.get_doc("Company", related_company)
        payment_entry.paid_to = owner_company_doc.default_receivable_account  # Will be adjusted to intercompany
        payment_entry.paid_from = owner_company_doc.default_receivable_account
        
        payment_entry.posting_date = self.doc.transaction_date
        payment_entry.reference_no = self.doc.reference_no
        payment_entry.reference_date = self.doc.transaction_date
        payment_entry.remarks = f"Receipt via {self.doc.company} - {self.doc.transaction_purposes}"
        
        exch_rate = row.exch_rate if hasattr(row, 'exch_rate') else 1
        amount = row.amount * exch_rate
        
        payment_entry.paid_amount = amount
        payment_entry.received_amount = amount
        payment_entry.source_exchange_rate = 1
        payment_entry.target_exchange_rate = 1
        
        # Add invoice references if available
        if hasattr(row, 'invoice_references') and row.invoice_references:
            payment_entry.append("references", {
                "reference_doctype": "Sales Invoice",
                "reference_name": row.invoice_references,
                "allocated_amount": amount
            })
        
        payment_entry.flags.ignore_mandatory = True
        payment_entry.flags.ignore_permissions = True
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()
        
        return payment_entry.name
    
    def create_owner_journal_entry(self, row, related_company):
        """Create journal entry for the real owner (non-Customer Receipt)"""
        transaction_purpose = f"{row.remark or 'Receipt'} received via {self.doc.company}"
        
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.naming_series = "BJV-.#####"
        journal_entry.paid_to_or_received_from = row.party_name or row.party
        journal_entry.transaction_description = transaction_purpose
        journal_entry.posting_date = self.doc.transaction_date
        journal_entry.reference_document_no = self.doc.name
        journal_entry.cheque_no = self.doc.reference_no
        journal_entry.cheque_date = self.doc.transaction_date
        journal_entry.company = related_company  # Owner company
        journal_entry.voucher_type = "Journal Entry"
        journal_entry.user_remark = transaction_purpose
        
        exch_rate = row.exch_rate if hasattr(row, 'exch_rate') else 1
        amount = row.amount * exch_rate
        
        # Debit: Intercompany Payable/Asset
        intercompany_account = frappe.db.get_value('Company', related_company, 'custom_intercompany_payable_account')
        if not intercompany_account:
            intercompany_account = frappe.get_doc("Company", related_company).default_payable_account
        
        journal_entry.append("accounts", {
            "account": intercompany_account,
            "debit_in_account_currency": amount,
            "debit": amount,
            "party_type": "Company",
            "party": self.doc.company,
            "user_remark": transaction_purpose,
            "against_account": row.party
        })
        
        # Credit: Revenue/Party Account
        self.validate_account_not_group(row.party)
        
        journal_entry.append("accounts", {
            "account": row.party,
            "credit_in_account_currency": amount,
            "credit": amount,
            "user_remark": transaction_purpose,
            "cost_center": row.cost_center if hasattr(row, 'cost_center') else None,
            "against_account": intercompany_account
        })
        
        journal_entry.set_total_debit_credit()
        journal_entry.flags.ignore_permissions = True
        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()
        
        return journal_entry.name


# ============================================
# UTILITY FUNCTIONS
# ============================================

def cancel_related_entries(doc):
    """Cancel related Journal and Payment Entries"""
    # Cancel Journal Entries
    related_journals = frappe.get_list(
        "Journal Entry",
        filters={"cheque_no": doc.reference_no, "docstatus": 1},
        fields=["name"]
    )
    
    for entry in related_journals:
        try:
            je = frappe.get_doc("Journal Entry", entry.name)
            je.cancel()
            frappe.logger().info(f"Cancelled Journal Entry {entry.name}")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Error cancelling JE {entry.name}")
    
    # Cancel Payment Entries
    related_payments = frappe.get_list(
        "Payment Entry",
        filters={"reference_no": doc.reference_no, "docstatus": 1},
        fields=["name"]
    )
    
    for entry in related_payments:
        try:
            pe = frappe.get_doc("Payment Entry", entry.name)
            pe.cancel()
            frappe.logger().info(f"Cancelled Payment Entry {entry.name}")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Error cancelling PE {entry.name}")


def format_currency_display(amount, currency):
    """Format currency for display"""
    try:
        return fmt_money(amount, currency=currency)
    except:
        # Fallback formatting
        return f"{currency} {flt(amount):,.2f}"


def send_customer_email_async(receipt_name):
    """Async wrapper for sending customer email"""
    try:
        receipt = frappe.get_doc("Receipts", receipt_name)
        receipt.send_customer_email()
        
        # Also send internal notification
        send_internal_receipt_notification(receipt)
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Async Email Error - {receipt_name}")


# ============================================
# WHITELISTED API FUNCTIONS
# ============================================

@frappe.whitelist()
def ai_smart_allocation(doc_name):
    """AI-powered smart invoice allocation"""
    doc = frappe.get_doc("Receipts", doc_name)
    
    if not doc.customer_id:
        frappe.throw(_("Please select a customer first"))
    
    # Get amount to allocate
    amount_to_allocate = doc.local_currency_amount or doc.amount_received or (doc.amount_received_in_fc * doc.exchange_rate if doc.amount_received_in_fc else 0)
    
    if not amount_to_allocate or amount_to_allocate <= 0:
        frappe.throw(_("Please enter a valid amount"))
    
    # Fetch outstanding invoices with intelligent sorting
    invoices = frappe.db.sql("""
        SELECT 
            name,
            posting_date,
            due_date,
            grand_total,
            outstanding_amount,
            payment_terms_template,
            DATEDIFF(CURDATE(), due_date) as days_overdue,
            CASE 
                WHEN DATEDIFF(CURDATE(), due_date) > 90 THEN 1
                WHEN DATEDIFF(CURDATE(), due_date) > 60 THEN 2
                WHEN DATEDIFF(CURDATE(), due_date) > 30 THEN 3
                WHEN DATEDIFF(CURDATE(), due_date) > 0 THEN 4
                ELSE 5
            END as priority
        FROM `tabSales Invoice`
        WHERE customer = %s
        AND docstatus = 1
        AND outstanding_amount > 0
        ORDER BY priority ASC, due_date ASC, posting_date ASC
    """, (doc.customer_id,), as_dict=True)
    
    if not invoices:
        frappe.msgprint(_("No outstanding invoices found for this customer"))
        return []
    
    # Clear existing allocations
    doc.receipts_reference = []
    
    # AI Allocation Logic
    remaining_amount = amount_to_allocate
    allocated_invoices = []
    
    for invoice in invoices:
        if remaining_amount <= 0:
            break
        
        allocated_amount = min(remaining_amount, invoice.outstanding_amount)
        
        doc.append("receipts_reference", {
            "date": invoice.posting_date,
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice.name,
            "due_date": invoice.due_date,
            "bill_no": invoice.name,
            "payment_term": invoice.payment_terms_template or "",
            "total_amount": invoice.grand_total,
            "outstanding_amount": invoice.outstanding_amount,
            "allocated_amount": allocated_amount,
            "exchange_rate": 1,
            "exchange_gain_loss": 0
        })
        
        allocated_invoices.append({
            "invoice": invoice.name,
            "amount": allocated_amount,
            "days_overdue": invoice.days_overdue,
            "priority": invoice.priority
        })
        
        remaining_amount -= allocated_amount
    
    # Save the document
    doc.save()
    
    # Return allocation summary
    return {
        "total_allocated": amount_to_allocate - remaining_amount,
        "remaining_amount": remaining_amount,
        "invoices_matched": len(allocated_invoices),
        "allocations": allocated_invoices
    }


@frappe.whitelist()
def preview_allocation(doc_name):
    """Generate HTML preview of invoice allocation"""
    doc = frappe.get_doc("Receipts", doc_name)
    
    if not doc.receipts_reference:
        return "<div class='alert alert-warning'>No invoice allocations found</div>"
    
    # Calculate totals
    total_allocated = sum(flt(row.allocated_amount) for row in doc.receipts_reference)
    total_outstanding = sum(flt(row.outstanding_amount) for row in doc.receipts_reference)
    
    # Generate HTML
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h3 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">
            Invoice Allocation Preview
        </h3>
        
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                <div style="text-align: center;">
                    <div style="font-size: 14px; opacity: 0.9;">Amount Received</div>
                    <div style="font-size: 24px; font-weight: bold; margin-top: 5px;">
                        {doc.receipt_currency} {flt(doc.local_currency_amount, 2):,.2f}
                    </div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 14px; opacity: 0.9;">Total Allocated</div>
                    <div style="font-size: 24px; font-weight: bold; margin-top: 5px;">
                        {doc.receipt_currency} {total_allocated:,.2f}
                    </div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 14px; opacity: 0.9;">Remaining</div>
                    <div style="font-size: 24px; font-weight: bold; margin-top: 5px;">
                        {doc.receipt_currency} {flt(doc.local_currency_amount - total_allocated, 2):,.2f}
                    </div>
                </div>
            </div>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <th style="padding: 15px; text-align: left; border: 1px solid #ddd;">Invoice</th>
                    <th style="padding: 15px; text-align: center; border: 1px solid #ddd;">Due Date</th>
                    <th style="padding: 15px; text-align: right; border: 1px solid #ddd;">Outstanding</th>
                    <th style="padding: 15px; text-align: right; border: 1px solid #ddd;">Allocated</th>
                    <th style="padding: 15px; text-align: right; border: 1px solid #ddd;">Remaining</th>
                    <th style="padding: 15px; text-align: center; border: 1px solid #ddd;">Status</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for i, row in enumerate(doc.receipts_reference):
        remaining = flt(row.outstanding_amount) - flt(row.allocated_amount)
        status = "Fully Paid" if remaining <= 0 else "Partially Paid"
        status_color = "#27ae60" if remaining <= 0 else "#f39c12"
        bg_color = "#f8f9fa" if i % 2 == 0 else "#ffffff"
        
        # Check if overdue
        is_overdue = False
        overdue_days = 0
        if row.due_date:
            overdue_days = date_diff(nowdate(), row.due_date)
            is_overdue = overdue_days > 0
        
        due_date_display = row.due_date or "N/A"
        if is_overdue:
            due_date_display = f"<span style='color: #e74c3c; font-weight: bold;'>{row.due_date} ({overdue_days} days overdue)</span>"
        
        html += f"""
            <tr style="background: {bg_color}; transition: background 0.3s;">
                <td style="padding: 12px; border: 1px solid #ddd;">
                    <strong>{row.reference_name}</strong>
                </td>
                <td style="padding: 12px; text-align: center; border: 1px solid #ddd;">
                    {due_date_display}
                </td>
                <td style="padding: 12px; text-align: right; border: 1px solid #ddd;">
                    {flt(row.outstanding_amount, 2):,.2f}
                </td>
                <td style="padding: 12px; text-align: right; border: 1px solid #ddd; font-weight: bold; color: #27ae60;">
                    {flt(row.allocated_amount, 2):,.2f}
                </td>
                <td style="padding: 12px; text-align: right; border: 1px solid #ddd;">
                    {remaining:,.2f}
                </td>
                <td style="padding: 12px; text-align: center; border: 1px solid #ddd;">
                    <span style="background: {status_color}; color: white; padding: 5px 10px; border-radius: 15px; font-size: 11px; font-weight: bold;">
                        {status}
                    </span>
                </td>
            </tr>
        """
    
    html += f"""
            </tbody>
            <tfoot>
                <tr style="background: #34495e; color: white; font-weight: bold;">
                    <td colspan="2" style="padding: 15px; border: 1px solid #2c3e50;">TOTAL</td>
                    <td style="padding: 15px; text-align: right; border: 1px solid #2c3e50;">
                        {total_outstanding:,.2f}
                    </td>
                    <td style="padding: 15px; text-align: right; border: 1px solid #2c3e50;">
                        {total_allocated:,.2f}
                    </td>
                    <td colspan="2" style="padding: 15px; border: 1px solid #2c3e50;"></td>
                </tr>
            </tfoot>
        </table>
    </div>
    """
    
    return html


@frappe.whitelist()
def send_bulk_acknowledgements(receipt_names, email_subject=None, include_pdf=1, custom_message=None):
    """Send acknowledgement emails for multiple receipts"""
    if isinstance(receipt_names, str):
        receipt_names = json.loads(receipt_names)
    
    if not receipt_names:
        frappe.throw(_("No receipts selected"))
    
    success_count = 0
    failed_count = 0
    failed_receipts = []
    
    # Process in batches of 50 for large volumes
    from frappe.utils import create_batch
    
    for batch in create_batch(receipt_names, 50):
        for receipt_name in batch:
            try:
                doc = frappe.get_doc("Receipts", receipt_name)
                
                # Check if submitted
                if doc.docstatus != 1:
                    failed_count += 1
                    failed_receipts.append({
                        "receipt": receipt_name,
                        "reason": "Not submitted"
                    })
                    continue
                
                # Check if customer has email
                if not doc.customer_id:
                    failed_count += 1
                    failed_receipts.append({
                        "receipt": receipt_name,
                        "reason": "No customer"
                    })
                    continue
                
                customer = frappe.get_doc("Customer", doc.customer_id)
                if not customer.email_id:
                    failed_count += 1
                    failed_receipts.append({
                        "receipt": receipt_name,
                        "reason": "No email address"
                    })
                    continue
                
                # Get print format
                print_format = frappe.db.get_single_value("Accounts Settings", "default_receipt_print_format") or "Standard"
                
                # Prepare email
                subject = email_subject or f"Payment Receipt - {doc.name}"
                
                message = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                        <h2 style="margin: 0; color: white;">Payment Receipt Confirmation</h2>
                    </div>
                    
                    <div style="padding: 30px; background: #ffffff; border: 1px solid #e0e0e0; border-top: none;">
                        <p style="font-size: 16px; color: #333;">Dear {doc.customer_name},</p>
                        
                        <p style="font-size: 14px; color: #666; line-height: 1.6;">
                            Thank you for your payment. We are pleased to confirm that we have received your payment.
                            Please find the details below:
                        </p>
                        
                        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background: #f9f9f9; border-radius: 8px; overflow: hidden;">
                            <tr>
                                <td style="padding: 15px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Receipt No:</td>
                                <td style="padding: 15px; border-bottom: 1px solid #e0e0e0; color: #666;">{doc.name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 15px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Date:</td>
                                <td style="padding: 15px; border-bottom: 1px solid #e0e0e0; color: #666;">{doc.transaction_date}</td>
                            </tr>
                            <tr>
                                <td style="padding: 15px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Amount Received:</td>
                                <td style="padding: 15px; border-bottom: 1px solid #e0e0e0; color: #27ae60; font-weight: bold; font-size: 16px;">
                                    {doc.amount_in_words or money_in_words(doc.local_currency_amount, doc.receipt_currency)}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 15px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Reference No:</td>
                                <td style="padding: 15px; border-bottom: 1px solid #e0e0e0; color: #666;">{doc.reference_no}</td>
                            </tr>
                            <tr>
                                <td style="padding: 15px; font-weight: bold; color: #333;">Payment Mode:</td>
                                <td style="padding: 15px; color: #666;">{doc.mode_of_payment or 'N/A'}</td>
                            </tr>
                        </table>
                """
                
                # Add custom message if provided
                if custom_message:
                    message += f"""
                        <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                            <p style="margin: 0; color: #1976d2; font-size: 14px;">
                                <strong>Note:</strong> {custom_message}
                            </p>
                        </div>
                    """
                
                # Add invoice details if available
                if doc.receipts_reference:
                    message += """
                        <div style="margin-top: 20px;">
                            <h3 style="color: #333; font-size: 16px; margin-bottom: 10px;">Allocated to Invoices:</h3>
                            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                                <thead>
                                    <tr style="background: #f5f5f5;">
                                        <th style="padding: 10px; text-align: left; border: 1px solid #e0e0e0;">Invoice</th>
                                        <th style="padding: 10px; text-align: right; border: 1px solid #e0e0e0;">Amount Allocated</th>
                                    </tr>
                                </thead>
                                <tbody>
                    """
                    
                    for ref in doc.receipts_reference:
                        if ref.allocated_amount and ref.allocated_amount > 0:
                            message += f"""
                                <tr>
                                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{ref.reference_name}</td>
                                    <td style="padding: 10px; text-align: right; border: 1px solid #e0e0e0; font-weight: bold;">
                                        {doc.receipt_currency} {flt(ref.allocated_amount, 2):,.2f}
                                    </td>
                                </tr>
                            """
                    
                    message += """
                                </tbody>
                            </table>
                        </div>
                    """
                
                message += f"""
                        <p style="font-size: 14px; color: #666; line-height: 1.6; margin-top: 20px;">
                            If you have any questions regarding this receipt, please don't hesitate to contact us.
                        </p>
                        
                        <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #e0e0e0;">
                            <p style="font-size: 14px; color: #333; margin: 0;">Best regards,</p>
                            <p style="font-size: 14px; color: #333; font-weight: bold; margin: 5px 0 0 0;">{doc.company}</p>
                        </div>
                    </div>
                    
                    <div style="background: #f5f5f5; padding: 20px; text-align: center; border-radius: 0 0 8px 8px;">
                        <p style="font-size: 12px; color: #999; margin: 0;">
                            This is an automated email. Please do not reply directly to this message.
                        </p>
                    </div>
                </div>
                """
                
                # Prepare attachments
                attachments = []
                if int(include_pdf):
                    try:
                        pdf_content = frappe.attach_print(
                            doctype=doc.doctype,
                            name=doc.name,
                            print_format=print_format,
                            doc=doc
                        )
                        attachments.append({
                            'fname': f"{doc.name}.pdf",
                            'fcontent': pdf_content
                        })
                    except Exception as e:
                        frappe.log_error(f"Failed to generate PDF for {doc.name}: {str(e)}", "Receipt PDF Error")
                
                # Send email
                frappe.sendmail(
                    recipients=[customer.email_id],
                    subject=subject,
                    message=message,
                    attachments=attachments,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                    now=True
                )
                
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                failed_receipts.append({
                    "receipt": receipt_name,
                    "reason": str(e)
                })
                frappe.log_error(frappe.get_traceback(), f"Bulk Acknowledgement Error - {receipt_name}")
        
        # Commit after each batch
        frappe.db.commit()
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_receipts": failed_receipts,
        "total": len(receipt_names)
    }


@frappe.whitelist()    
def send_internal_receipt_notification(receipt_doc):
    """Send receipt notification to internal users (issued_by, authorised_by)"""
    # Handle if receipt_doc is passed as string (document name)
    if isinstance(receipt_doc, str):
        receipt_doc = frappe.get_doc("Receipts", receipt_doc)
    
    try:
        recipients = []
        
        # Add issued_by if exists
        if receipt_doc.issued_by:
            issued_by_email = frappe.db.get_value('User', receipt_doc.issued_by, 'email')
            if issued_by_email:
                recipients.append(issued_by_email)
        
        # Add authorised_by if exists
        if receipt_doc.authorised_by:
            auth_email = frappe.db.get_value('User', receipt_doc.authorised_by, 'email')
            if auth_email:
                recipients.append(auth_email)
        
        # Check if we have any recipients
        if not recipients:
            frappe.log_error("No internal recipients found for receipt notification", 
                "Receipt Internal Notification Warning")
            return
        
        # Format amount for display
        amount_display = format_currency_display(
            receipt_doc.amount_received or receipt_doc.amount_received_in_fc, 
            receipt_doc.receipt_currency
        )
        
        # Build email message
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0; color: white;">Receipt Processed Successfully</h2>
            </div>
            
            <div style="padding: 30px; background: #ffffff;">
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Receipt No:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; color: #666;">{receipt_doc.name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Customer/Payer:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; color: #666;">{receipt_doc.customer_name or receipt_doc.payer_name or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Amount:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; color: #27ae60; font-weight: bold; font-size: 16px;">{amount_display}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Reference No:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; color: #666;">{receipt_doc.reference_no or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Transaction Date:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; color: #666;">{receipt_doc.transaction_date or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; font-weight: bold; color: #333;">Amount in Words:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e0e0e0; color: #666; font-style: italic;">{receipt_doc.amount_in_words or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold; color: #333;">Transaction Type:</td>
                        <td style="padding: 10px; color: #666;">{receipt_doc.trans_type or 'N/A'}</td>
                    </tr>
                </table>
                
                <div style="margin-top: 20px; padding: 15px; background: #f0f8ff; border-left: 4px solid #667eea; border-radius: 4px;">
                    <p style="margin: 0; color: #333; font-size: 14px;">
                        <strong>Note:</strong> This receipt has been successfully processed and saved in the system.
                    </p>
                </div>
                
                <div style="margin-top: 30px; text-align: center;">
                    <a href="{get_url()}/app/receipts/{receipt_doc.name}" 
                       style="display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        View Receipt
                    </a>
                </div>
            </div>
            
            <div style="background: #f5f5f5; padding: 15px; text-align: center; border-top: 1px solid #e0e0e0;">
                <p style="margin: 0; color: #999; font-size: 12px;">
                    This is an automated notification from {receipt_doc.company or 'the system'}
                </p>
            </div>
        </div>
        """
        
        # Send email
        frappe.sendmail(
            recipients=list(set(recipients)),  # Remove duplicates
            subject=f"Receipt Processed - {receipt_doc.name}",
            message=message,
            reference_doctype="Receipts",
            reference_name=receipt_doc.name,
            now=True
        )
        
        frappe.logger().info(f"Internal notification sent to {len(set(recipients))} recipient(s)")
        
        return {
            "success": True,
            "recipients": list(set(recipients)),
            "message": "Email sent successfully"
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Receipt Internal Notification Error")
        return {
            "success": False,
            "error": str(e)
        }