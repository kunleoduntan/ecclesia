# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Receipt Utilities Module
Common utility functions for Receipts DocType
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, fmt_money, get_url_to_form
from frappe.utils.data import money_in_words
import json


# ==================== Amount Conversion Utilities ====================

def get_amount_in_words(amount, currency="NGN"):
    """
    Convert amount to words
    Supports multiple currencies
    """
    try:
        if not amount or amount == 0:
            return "Zero Only"
        
        currency_info = get_currency_info(currency)
        amount_in_words = money_in_words(amount, currency_info['name'])
        
        return amount_in_words
    
    except Exception as e:
        frappe.log_error(f"Error converting amount to words: {str(e)}", "Amount Conversion Error")
        return f"{currency} {amount:,.2f}"


def get_currency_info(currency):
    """Get currency information"""
    currency_map = {
        'NGN': {'name': 'Naira', 'symbol': '₦', 'fraction': 'Kobo'},
        'USD': {'name': 'Dollar', 'symbol': '$', 'fraction': 'Cent'},
        'GBP': {'name': 'Pound', 'symbol': '£', 'fraction': 'Pence'},
        'EUR': {'name': 'Euro', 'symbol': '€', 'fraction': 'Cent'},
    }
    
    return currency_map.get(currency, {'name': currency, 'symbol': currency, 'fraction': ''})


def format_currency_display(amount, currency, include_symbol=True):
    """Format currency for display"""
    if not amount:
        return "0.00"
    
    currency_info = get_currency_info(currency)
    formatted_amount = f"{amount:,.2f}"
    
    if include_symbol:
        return f"{currency_info['symbol']}{formatted_amount}"
    
    return formatted_amount


# ==================== Document Linking Utilities ====================

def link_documents(receipt_doc):
    """
    Link receipt to created accounting entries
    Updates the connections tab
    """
    try:
        # This function is called after accounting entries are created
        # Links are automatically created via reference_no matching
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Error linking documents: {str(e)}", "Document Linking Error")


def get_document_links(receipt_name):
    """Get all linked documents for a receipt"""
    receipt = frappe.get_doc('Receipts', receipt_name)
    
    links = {
        'journal_entries': [],
        'payment_entries': [],
        'sales_invoices': [],
        'deferred_revenue_entries': []
    }
    
    # Journal Entries
    je_list = frappe.get_all('Journal Entry',
        filters={'cheque_no': receipt.reference_no},
        fields=['name', 'posting_date', 'total_debit', 'docstatus'],
        order_by='posting_date desc'
    )
    
    for je in je_list:
        je['url'] = get_url_to_form('Journal Entry', je.name)
        links['journal_entries'].append(je)
    
    # Payment Entries
    pe_list = frappe.get_all('Payment Entry',
        filters={'reference_no': receipt.reference_no},
        fields=['name', 'posting_date', 'paid_amount', 'docstatus'],
        order_by='posting_date desc'
    )
    
    for pe in pe_list:
        pe['url'] = get_url_to_form('Payment Entry', pe.name)
        links['payment_entries'].append(pe)
    
    # Sales Invoices
    if receipt.receipt_reference:
        for ref in receipt.receipt_reference:
            if ref.reference_name:
                inv = frappe.get_doc('Sales Invoice', ref.reference_name)
                links['sales_invoices'].append({
                    'name': inv.name,
                    'posting_date': inv.posting_date,
                    'grand_total': inv.grand_total,
                    'outstanding_amount': inv.outstanding_amount,
                    'url': get_url_to_form('Sales Invoice', inv.name)
                })
    
    # Deferred Revenue Journal Entries
    if receipt.defer_revenue and receipt.revenue_schedule:
        schedules = frappe.get_all('Schedule of Deferred Revenue',
            filters={'source_doc_ref': receipt.name, 'posted': 1},
            fields=['name', 'journal_entry', 'date', 'amount']
        )
        
        for schedule in schedules:
            if schedule.journal_entry:
                links['deferred_revenue_entries'].append({
                    'name': schedule.journal_entry,
                    'date': schedule.date,
                    'amount': schedule.amount,
                    'url': get_url_to_form('Journal Entry', schedule.journal_entry)
                })
    
    return links


@frappe.whitelist()
def get_linked_accounting_entries(receipt_name):
    """Get linked accounting entries for display"""
    receipt = frappe.get_doc('Receipts', receipt_name)
    
    result = {
        'journal_entries': [],
        'payment_entries': []
    }
    
    # Get Journal Entries
    je_list = frappe.get_all('Journal Entry',
        filters={
            'cheque_no': receipt.reference_no
        },
        fields=['name', 'posting_date', 'total_debit', 'docstatus', 'voucher_type'],
        order_by='creation desc'
    )
    
    result['journal_entries'] = je_list
    
    # Get Payment Entries
    pe_list = frappe.get_all('Payment Entry',
        filters={
            'reference_no': receipt.reference_no
        },
        fields=['name', 'posting_date', 'paid_amount', 'docstatus', 'payment_type'],
        order_by='creation desc'
    )
    
    result['payment_entries'] = pe_list
    
    return result


# ==================== Notification Utilities ====================

class ReceiptNotifier:
    """Handle receipt notifications"""
    
    @staticmethod
    def send_approval_notification(receipt_doc):
        """Send notification for receipt approval"""
        try:
            approvers = ReceiptNotifier._get_approvers(receipt_doc)
            
            if not approvers:
                return
            
            message = f"""
            <h3>Receipt Approval Required</h3>
            <p><b>Receipt No:</b> {receipt_doc.name}</p>
            <p><b>Customer:</b> {receipt_doc.customer_name or receipt_doc.payer_name}</p>
            <p><b>Amount:</b> {format_currency_display(receipt_doc.amount_received or receipt_doc.amount_received_in_fc, receipt_doc.receipt_currency)}</p>
            <p><b>Purpose:</b> {receipt_doc.transaction_purposes}</p>
            <p><a href="{get_url_to_form('Receipts', receipt_doc.name)}">Click here to review</a></p>
            """
            
            for approver in approvers:
                frappe.sendmail(
                    recipients=[approver],
                    subject=f"Receipt Approval Required - {receipt_doc.name}",
                    message=message
                )
            
        except Exception as e:
            frappe.log_error(f"Error sending approval notification: {str(e)}", 
                "Receipt Notification Error")
    
    @staticmethod
    def send_receipt_confirmation(receipt_doc):
        """Send receipt confirmation notification"""
        try:
            recipients = [receipt_doc.issued_by]
            if receipt_doc.authorised_by:
                recipients.append(receipt_doc.authorised_by)
            
            # Optionally notify customer
            if receipt_doc.customer_id:
                customer_email = frappe.db.get_value('Customer', receipt_doc.customer_id, 'email_id')
                if customer_email:
                    recipients.append(customer_email)
            
            message = f"""
            <h3>Receipt Processed Successfully</h3>
            <p><b>Receipt No:</b> {receipt_doc.name}</p>
            <p><b>Customer:</b> {receipt_doc.customer_name or receipt_doc.payer_name}</p>
            <p><b>Amount:</b> {format_currency_display(receipt_doc.amount_received or receipt_doc.amount_received_in_fc, receipt_doc.receipt_currency)}</p>
            <p><b>Reference:</b> {receipt_doc.reference_no}</p>
            <p><b>Date:</b> {receipt_doc.transaction_date}</p>
            <p><b>Amount in Words:</b> {receipt_doc.amount_in_words}</p>
            """
            
            frappe.sendmail(
                recipients=list(set(recipients)),
                subject=f"Receipt Processed - {receipt_doc.name}",
                message=message
            )
            
        except Exception as e:
            frappe.log_error(f"Error sending confirmation: {str(e)}", 
                "Receipt Notification Error")
    
    @staticmethod
    def send_customer_receipt_acknowledgement(receipt_doc):
        """Send receipt acknowledgement to customer"""
        try:
            if not receipt_doc.customer_id:
                return
            
            customer_email = frappe.db.get_value('Customer', receipt_doc.customer_id, 'email_id')
            if not customer_email:
                return
            
            message = f"""
            <h3>Receipt Acknowledgement</h3>
            <p>Dear {receipt_doc.customer_name},</p>
            <p>This is to acknowledge receipt of your payment.</p>
            <p><b>Receipt No:</b> {receipt_doc.name}</p>
            <p><b>Amount Received:</b> {format_currency_display(receipt_doc.amount_received or receipt_doc.amount_received_in_fc, receipt_doc.receipt_currency)}</p>
            <p><b>Amount in Words:</b> {receipt_doc.amount_in_words}</p>
            <p><b>Reference:</b> {receipt_doc.reference_no}</p>
            <p><b>Date:</b> {receipt_doc.transaction_date}</p>
            <p><b>Payment Method:</b> {receipt_doc.mode_of_payment}</p>
            <p>Thank you for your payment.</p>
            """
            
            frappe.sendmail(
                recipients=[customer_email],
                subject=f"Payment Receipt - {receipt_doc.name}",
                message=message
            )
            
        except Exception as e:
            frappe.log_error(f"Error sending customer acknowledgement: {str(e)}", 
                "Receipt Notification Error")
    
    @staticmethod
    def _get_approvers(receipt_doc):
        """Get list of approvers for receipt"""
        approvers = []
        
        # Get users with Accounts Manager role
        users = frappe.get_all('Has Role',
            filters={'role': 'Accounts Manager'},
            fields=['parent']
        )
        approvers = [u.parent for u in users]
        
        return list(set(approvers))


# ==================== Validation Utilities ====================

def validate_bank_balance(bank_account, amount, transaction_date):
    """Validate bank balance (for reference, receipts increase balance)"""
    try:
        balance = frappe.db.sql("""
            SELECT 
                SUM(debit_in_account_currency - credit_in_account_currency) as balance
            FROM `tabGL Entry`
            WHERE 
                account = %(account)s
                AND posting_date <= %(date)s
                AND is_cancelled = 0
        """, {
            'account': frappe.db.get_value('Bank Account', bank_account, 'account'),
            'date': transaction_date
        }, as_dict=1)
        
        current_balance = balance[0].balance if balance else 0
        
        # For receipts, we're adding to the balance
        new_balance = current_balance + amount
        
        return {
            'valid': True,
            'current_balance': current_balance,
            'new_balance': new_balance,
            'message': f"Balance will increase to {new_balance:,.2f}"
        }
    
    except Exception as e:
        frappe.log_error(f"Error checking bank balance: {str(e)}", "Balance Check Error")
        return {
            'valid': True,
            'message': "Could not verify balance"
        }


def check_duplicate_receipt(customer, amount, transaction_date, reference_no, current_doc=None):
    """Check for potential duplicate receipts"""
    date_from = frappe.utils.add_days(transaction_date, -7)
    date_to = frappe.utils.add_days(transaction_date, 7)
    
    filters = {
        'customer_id': customer,
        'amount_received': amount,
        'transaction_date': ['between', [date_from, date_to]],
        'docstatus': ['!=', 2]
    }
    
    if current_doc:
        filters['name'] = ['!=', current_doc]
    
    duplicates = frappe.get_all('Receipts',
        filters=filters,
        fields=['name', 'transaction_date', 'reference_no']
    )
    
    if duplicates:
        return {
            'is_duplicate': True,
            'possible_duplicates': duplicates
        }
    
    return {'is_duplicate': False}


def check_customer_outstanding(customer, company):
    """Check customer's outstanding amount"""
    try:
        outstanding = frappe.db.sql("""
            SELECT 
                COUNT(*) as invoice_count,
                SUM(outstanding_amount) as total_outstanding,
                SUM(CASE WHEN DATEDIFF(CURDATE(), due_date) > 0 THEN outstanding_amount ELSE 0 END) as overdue_amount
            FROM `tabSales Invoice`
            WHERE 
                customer = %(customer)s
                AND company = %(company)s
                AND docstatus = 1
                AND outstanding_amount > 0
        """, {
            'customer': customer,
            'company': company
        }, as_dict=1)
        
        return outstanding[0] if outstanding else {
            'invoice_count': 0,
            'total_outstanding': 0,
            'overdue_amount': 0
        }
    
    except Exception as e:
        frappe.log_error(f"Error checking customer outstanding: {str(e)}", "Outstanding Check Error")
        return None


# ==================== Batch Processing Utilities ====================

class BatchReceiptProcessor:
    """Process multiple receipts in batch"""
    
    @staticmethod
    def process_batch(receipt_names):
        """Process a batch of receipts"""
        results = []
        
        for receipt_name in receipt_names:
            try:
                receipt = frappe.get_doc('Receipts', receipt_name)
                
                if receipt.docstatus != 0:
                    results.append({
                        'receipt': receipt_name,
                        'status': 'Skipped',
                        'message': 'Already submitted or cancelled'
                    })
                    continue
                
                receipt.submit()
                
                results.append({
                    'receipt': receipt_name,
                    'status': 'Success',
                    'message': 'Submitted successfully'
                })
            
            except Exception as e:
                results.append({
                    'receipt': receipt_name,
                    'status': 'Error',
                    'message': str(e)
                })
                frappe.log_error(f"Error processing batch receipt {receipt_name}: {str(e)}",
                    "Batch Processing Error")
        
        return results
    
    @staticmethod
    def bulk_approve(receipt_names, user):
        """Bulk approve receipts"""
        results = []
        
        for receipt_name in receipt_names:
            try:
                receipt = frappe.get_doc('Receipts', receipt_name)
                
                receipt.approved_by = user
                receipt.approval_date = nowdate()
                receipt.receipt_status = 'Approved'
                
                receipt.save()
                
                results.append({
                    'receipt': receipt_name,
                    'status': 'Approved'
                })
            
            except Exception as e:
                results.append({
                    'receipt': receipt_name,
                    'status': 'Error',
                    'message': str(e)
                })
        
        return results
    
    @staticmethod
    def bulk_allocate_receipts(receipt_names):
        """Bulk allocate receipts to invoices using AI"""
        results = []
        
        for receipt_name in receipt_names:
            try:
                from general.receipt_accounting.receipt_invoice_matcher import apply_smart_allocation
                
                result = apply_smart_allocation(receipt_name)
                
                results.append({
                    'receipt': receipt_name,
                    'status': 'Allocated',
                    'allocated_invoices': result.get('result', {}).get('total_invoices', 0)
                })
            
            except Exception as e:
                results.append({
                    'receipt': receipt_name,
                    'status': 'Error',
                    'message': str(e)
                })
        
        return results


# ==================== Analysis Utilities ====================

def get_receipt_analytics(company, from_date, to_date):
    """Get receipt analytics for dashboard"""
    data = frappe.db.sql("""
        SELECT 
            trans_type,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_received)) as total_amount,
            AVG(COALESCE(local_currency_amount, amount_received)) as avg_amount,
            receipt_status,
            receipt_currency
        FROM `tabReceipts`
        WHERE 
            company = %(company)s
            AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus != 2
        GROUP BY trans_type, receipt_status, receipt_currency
    """, {
        'company': company,
        'from_date': from_date,
        'to_date': to_date
    }, as_dict=1)
    
    return data


def get_customer_receipt_summary(customer, from_date, to_date):
    """Get receipt summary for a customer"""
    receipts = frappe.db.sql("""
        SELECT 
            name,
            transaction_date,
            COALESCE(local_currency_amount, amount_received) as amount_received,
            reference_no,
            transaction_purposes,
            receipt_status,
            wht_amount,
            COALESCE(net_amount, local_currency_amount, amount_received) as net_amount
        FROM `tabReceipts`
        WHERE 
            customer_id = %(customer)s
            AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
        ORDER BY transaction_date DESC
    """, {
        'customer': customer,
        'from_date': from_date,
        'to_date': to_date
    }, as_dict=1)
    
    summary = {
        'total_receipts': len(receipts),
        'total_amount': sum([p.amount_received for p in receipts]),
        'total_wht': sum([p.wht_amount or 0 for p in receipts]),
        'total_net': sum([p.net_amount or p.amount_received for p in receipts]),
        'receipts': receipts
    }
    
    return summary


def get_daily_collection_summary(company, date=None):
    """Get daily collection summary"""
    if not date:
        date = nowdate()
    
    summary = frappe.db.sql("""
        SELECT 
            mode_of_payment,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_received)) as total,
            receipt_currency
        FROM `tabReceipts`
        WHERE 
            company = %(company)s
            AND transaction_date = %(date)s
            AND docstatus = 1
        GROUP BY mode_of_payment, receipt_currency
    """, {
        'company': company,
        'date': date
    }, as_dict=1)
    
    return summary


def get_customer_aging_with_receipts(company):
    """Get customer aging considering recent receipts"""
    aging = frappe.db.sql("""
        SELECT 
            si.customer,
            si.customer_name,
            SUM(si.outstanding_amount) as total_outstanding,
            SUM(CASE WHEN DATEDIFF(CURDATE(), si.due_date) BETWEEN 0 AND 30 THEN si.outstanding_amount ELSE 0 END) as current,
            SUM(CASE WHEN DATEDIFF(CURDATE(), si.due_date) BETWEEN 31 AND 60 THEN si.outstanding_amount ELSE 0 END) as days_30_60,
            SUM(CASE WHEN DATEDIFF(CURDATE(), si.due_date) BETWEEN 61 AND 90 THEN si.outstanding_amount ELSE 0 END) as days_61_90,
            SUM(CASE WHEN DATEDIFF(CURDATE(), si.due_date) > 90 THEN si.outstanding_amount ELSE 0 END) as over_90,
            (SELECT SUM(amount_received) FROM `tabReceipts` WHERE customer_id = si.customer AND docstatus = 1 AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)) as receipts_last_30_days
        FROM `tabSales Invoice` si
        WHERE 
            si.company = %(company)s
            AND si.docstatus = 1
            AND si.outstanding_amount > 0
        GROUP BY si.customer, si.customer_name
        ORDER BY total_outstanding DESC
    """, {
        'company': company
    }, as_dict=1)
    
    return aging


# ==================== Whitelisted API Methods ====================

@frappe.whitelist()
def get_receipt_summary_card(receipt_name):
    """Get receipt summary for display card"""
    receipt = frappe.get_doc('Receipts', receipt_name)
    
    summary = {
        'receipt_no': receipt.name,
        'customer': receipt.customer_name or receipt.payer_name,
        'amount': format_currency_display(
            receipt.amount_received or receipt.amount_received_in_fc,
            receipt.receipt_currency
        ),
        'amount_in_words': receipt.amount_in_words,
        'status': receipt.receipt_status,
        'date': receipt.transaction_date,
        'reference': receipt.reference_no,
        'purpose': receipt.transaction_purposes,
        'mode_of_payment': receipt.mode_of_payment
    }
    
    if receipt.deduct_wht:
        summary['wht_amount'] = format_currency_display(receipt.wht_amount, receipt.receipt_currency)
        summary['net_amount'] = format_currency_display(receipt.net_amount, receipt.receipt_currency)
    
    # Get customer outstanding
    if receipt.customer_id:
        outstanding_info = check_customer_outstanding(receipt.customer_id, receipt.company)
        if outstanding_info:
            summary['customer_outstanding'] = outstanding_info
    
    summary['links'] = get_document_links(receipt_name)
    
    return summary


@frappe.whitelist()
def send_receipt_notification(receipt_name, notification_type='confirmation'):
    """Send receipt notification"""
    receipt = frappe.get_doc('Receipts', receipt_name)
    
    if notification_type == 'approval':
        ReceiptNotifier.send_approval_notification(receipt)
    elif notification_type == 'confirmation':
        ReceiptNotifier.send_receipt_confirmation(receipt)
    elif notification_type == 'customer_acknowledgement':
        ReceiptNotifier.send_customer_receipt_acknowledgement(receipt)
    
    return {'success': True, 'message': 'Notification sent'}


@frappe.whitelist()
def check_receipt_duplicates(customer, amount, transaction_date, current_doc=None):
    """Check for duplicate receipts"""
    return check_duplicate_receipt(customer, amount, transaction_date, None, current_doc)


@frappe.whitelist()
def batch_process_receipts(receipt_names):
    """Process multiple receipts"""
    if isinstance(receipt_names, str):
        receipt_names = json.loads(receipt_names)
    
    return BatchReceiptProcessor.process_batch(receipt_names)


@frappe.whitelist()
def batch_allocate_receipts(receipt_names):
    """Batch allocate receipts to invoices"""
    if isinstance(receipt_names, str):
        receipt_names = json.loads(receipt_names)
    
    return BatchReceiptProcessor.bulk_allocate_receipts(receipt_names)


@frappe.whitelist()
def export_receipts_report(filters):
    """Export Receipts to Excel"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    # Implementation for Excel export
    frappe.msgprint(_("Export functionality will be implemented"))
    return {'success': True}


@frappe.whitelist()
def get_receipt_dashboard_data(company, from_date=None, to_date=None):
    """Get dashboard analytics"""
    if not from_date:
        from_date = frappe.utils.add_months(nowdate(), -1)
    if not to_date:
        to_date = nowdate()
    
    return get_receipt_analytics(company, from_date, to_date)


@frappe.whitelist()
def get_daily_collection_report(company, date=None):
    """Get daily collection report"""
    return get_daily_collection_summary(company, date)


@frappe.whitelist()
def get_customer_aging_report(company):
    """Get customer aging report with recent receipt information"""
    return get_customer_aging_with_receipts(company)


@frappe.whitelist()
def get_customer_outstanding_info(customer, company):
    """Get customer outstanding information"""
    return check_customer_outstanding(customer, company)


@frappe.whitelist()
def reconcile_customer_account(customer, company):
    """Reconcile customer account - match receipts to invoices"""
    # This would implement auto-reconciliation logic
    frappe.msgprint(_("Reconciliation functionality will be implemented"))
    return {'success': True}


@frappe.whitelist()
def generate_receipt_voucher(receipt_name):
    """Generate printable receipt voucher"""
    receipt = frappe.get_doc('Receipts', receipt_name)
    
    # Return receipt details for printing
    return {
        'receipt': receipt.as_dict(),
        'amount_in_words': get_amount_in_words(
            receipt.amount_received or receipt.amount_received_in_fc,
            receipt.receipt_currency
        )
    }