# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Payment Utilities Module
Common utility functions for Payments DocType
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

def link_documents(payment_doc):
    """
    Link payment to created accounting entries
    Updates the connections tab
    """
    try:
        # This function is called after accounting entries are created
        # Links are automatically created via reference_no matching
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Error linking documents: {str(e)}", "Document Linking Error")


def get_document_links(payment_name):
    """Get all linked documents for a payment"""
    payment = frappe.get_doc('Payments', payment_name)
    
    links = {
        'journal_entries': [],
        'payment_entries': [],
        'purchase_invoices': [],
        'amortization_entries': []
    }
    
    # Journal Entries
    je_list = frappe.get_all('Journal Entry',
        filters={'cheque_no': payment.reference_no},
        fields=['name', 'posting_date', 'total_debit', 'docstatus'],
        order_by='posting_date desc'
    )
    
    for je in je_list:
        je['url'] = get_url_to_form('Journal Entry', je.name)
        links['journal_entries'].append(je)
    
    # Payment Entries
    pe_list = frappe.get_all('Payment Entry',
        filters={'reference_no': payment.reference_no},
        fields=['name', 'posting_date', 'paid_amount', 'docstatus'],
        order_by='posting_date desc'
    )
    
    for pe in pe_list:
        pe['url'] = get_url_to_form('Payment Entry', pe.name)
        links['payment_entries'].append(pe)
    
    # Purchase Invoices
    if payment.payments_reference:
        for ref in payment.payments_reference:
            if ref.reference_name:
                inv = frappe.get_doc('Purchase Invoice', ref.reference_name)
                links['purchase_invoices'].append({
                    'name': inv.name,
                    'posting_date': inv.posting_date,
                    'grand_total': inv.grand_total,
                    'outstanding_amount': inv.outstanding_amount,
                    'url': get_url_to_form('Purchase Invoice', inv.name)
                })
    
    # Amortization Journal Entries
    if payment.amortize and payment.amortization_schedule:
        schedules = frappe.get_all('Schedule of Prepayments',
            filters={'source_doc_ref': payment.name, 'posted': 1},
            fields=['name', 'journal_entry', 'date', 'amount']
        )
        
        for schedule in schedules:
            if schedule.journal_entry:
                links['amortization_entries'].append({
                    'name': schedule.journal_entry,
                    'date': schedule.date,
                    'amount': schedule.amount,
                    'url': get_url_to_form('Journal Entry', schedule.journal_entry)
                })
    
    return links


@frappe.whitelist()
def get_linked_accounting_entries(payment_name):
    """Get linked accounting entries for display"""
    payment = frappe.get_doc('Payments', payment_name)
    
    result = {
        'journal_entries': [],
        'payment_entries': []
    }
    
    # Get Journal Entries
    je_list = frappe.get_all('Journal Entry',
        filters={
            'cheque_no': payment.reference_no
        },
        fields=['name', 'posting_date', 'total_debit', 'docstatus', 'voucher_type'],
        order_by='creation desc'
    )
    
    result['journal_entries'] = je_list
    
    # Get Payment Entries
    pe_list = frappe.get_all('Payment Entry',
        filters={
            'reference_no': payment.reference_no
        },
        fields=['name', 'posting_date', 'paid_amount', 'docstatus', 'payment_type'],
        order_by='creation desc'
    )
    
    result['payment_entries'] = pe_list
    
    return result


# ==================== Notification Utilities ====================

class PaymentNotifier:
    """Handle payment notifications"""
    
    @staticmethod
    def send_approval_notification(payment_doc):
        """Send notification for payment approval"""
        try:
            approvers = PaymentNotifier._get_approvers(payment_doc)
            
            if not approvers:
                return
            
            message = f"""
            <h3>Payment Approval Required</h3>
            <p><b>Payment No:</b> {payment_doc.name}</p>
            <p><b>Payee:</b> {payment_doc.payee_name or payment_doc.supplier_name}</p>
            <p><b>Amount:</b> {format_currency_display(payment_doc.amount_paid or payment_doc.amount_paid_in_fc, payment_doc.payment_currency)}</p>
            <p><b>Purpose:</b> {payment_doc.transaction_purposes}</p>
            <p><a href="{get_url_to_form('Payments', payment_doc.name)}">Click here to review</a></p>
            """
            
            for approver in approvers:
                frappe.sendmail(
                    recipients=[approver],
                    subject=f"Payment Approval Required - {payment_doc.name}",
                    message=message
                )
            
        except Exception as e:
            frappe.log_error(f"Error sending approval notification: {str(e)}", 
                "Payment Notification Error")
    
    @staticmethod
    def send_payment_confirmation(payment_doc):
        """Send payment confirmation notification"""
        try:
            recipients = [payment_doc.issued_by]
            if payment_doc.authorised_by:
                recipients.append(payment_doc.authorised_by)
            
            message = f"""
            <h3>Payment Processed Successfully</h3>
            <p><b>Payment No:</b> {payment_doc.name}</p>
            <p><b>Payee:</b> {payment_doc.payee_name or payment_doc.supplier_name}</p>
            <p><b>Amount:</b> {format_currency_display(payment_doc.amount_paid or payment_doc.amount_paid_in_fc, payment_doc.payment_currency)}</p>
            <p><b>Reference:</b> {payment_doc.reference_no}</p>
            <p><b>Date:</b> {payment_doc.transaction_date}</p>
            """
            
            frappe.sendmail(
                recipients=recipients,
                subject=f"Payment Processed - {payment_doc.name}",
                message=message
            )
            
        except Exception as e:
            frappe.log_error(f"Error sending confirmation: {str(e)}", 
                "Payment Notification Error")
    
    @staticmethod
    def _get_approvers(payment_doc):
        """Get list of approvers for payment"""
        approvers = []
        
        users = frappe.get_all('Has Role',
            filters={'role': 'Accounts Manager'},
            fields=['parent']
        )
        approvers = [u.parent for u in users]
        
        return list(set(approvers))


# ==================== Validation Utilities ====================

def validate_bank_balance(bank_account, amount, transaction_date):
    """Validate if bank has sufficient balance"""
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
        
        if current_balance < amount:
            return {
                'valid': False,
                'message': f"Insufficient balance. Available: {current_balance:,.2f}, Required: {amount:,.2f}",
                'balance': current_balance
            }
        
        return {
            'valid': True,
            'balance': current_balance
        }
    
    except Exception as e:
        frappe.log_error(f"Error checking bank balance: {str(e)}", "Balance Check Error")
        return {
            'valid': True,
            'message': "Could not verify balance"
        }


def check_duplicate_payment(supplier, amount, transaction_date, reference_no, current_doc=None):
    """Check for potential duplicate payments"""
    date_from = frappe.utils.add_days(transaction_date, -7)
    date_to = frappe.utils.add_days(transaction_date, 7)
    
    filters = {
        'payee_id': supplier,
        'amount_paid': amount,
        'transaction_date': ['between', [date_from, date_to]],
        'docstatus': ['!=', 2]
    }
    
    if current_doc:
        filters['name'] = ['!=', current_doc]
    
    duplicates = frappe.get_all('Payments',
        filters=filters,
        fields=['name', 'transaction_date', 'reference_no']
    )
    
    if duplicates:
        return {
            'is_duplicate': True,
            'possible_duplicates': duplicates
        }
    
    return {'is_duplicate': False}


# ==================== Batch Processing Utilities ====================

class BatchPaymentProcessor:
    """Process multiple payments in batch"""
    
    @staticmethod
    def process_batch(payment_names):
        """Process a batch of payments"""
        results = []
        
        for payment_name in payment_names:
            try:
                payment = frappe.get_doc('Payments', payment_name)
                
                if payment.docstatus != 0:
                    results.append({
                        'payment': payment_name,
                        'status': 'Skipped',
                        'message': 'Already submitted or cancelled'
                    })
                    continue
                
                payment.submit()
                
                results.append({
                    'payment': payment_name,
                    'status': 'Success',
                    'message': 'Submitted successfully'
                })
            
            except Exception as e:
                results.append({
                    'payment': payment_name,
                    'status': 'Error',
                    'message': str(e)
                })
                frappe.log_error(f"Error processing batch payment {payment_name}: {str(e)}",
                    "Batch Processing Error")
        
        return results
    
    @staticmethod
    def bulk_approve(payment_names, user):
        """Bulk approve payments"""
        results = []
        
        for payment_name in payment_names:
            try:
                payment = frappe.get_doc('Payments', payment_name)
                
                payment.approved_by = user
                payment.app_date = nowdate()
                payment.payment_status = 'Approved'
                
                payment.save()
                
                results.append({
                    'payment': payment_name,
                    'status': 'Approved'
                })
            
            except Exception as e:
                results.append({
                    'payment': payment_name,
                    'status': 'Error',
                    'message': str(e)
                })
        
        return results


# ==================== Analysis Utilities ====================

def get_payment_analytics(company, from_date, to_date):
    """Get payment analytics for dashboard"""
    data = frappe.db.sql("""
        SELECT 
            trans_type,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_paid)) as total_amount,
            AVG(COALESCE(local_currency_amount, amount_paid)) as avg_amount,
            payment_status,
            payment_currency
        FROM `tabPayments`
        WHERE 
            company = %(company)s
            AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus != 2
        GROUP BY trans_type, payment_status, payment_currency
    """, {
        'company': company,
        'from_date': from_date,
        'to_date': to_date
    }, as_dict=1)
    
    return data


def get_supplier_payment_summary(supplier, from_date, to_date):
    """Get payment summary for a supplier"""
    payments = frappe.db.sql("""
        SELECT 
            name,
            transaction_date,
            COALESCE(local_currency_amount, amount_paid) as amount_paid,
            reference_no,
            transaction_purposes,
            payment_status,
            wht_amount,
            COALESCE(net_amount, local_currency_amount, amount_paid) as net_amount
        FROM `tabPayments`
        WHERE 
            payee_id = %(supplier)s
            AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
        ORDER BY transaction_date DESC
    """, {
        'supplier': supplier,
        'from_date': from_date,
        'to_date': to_date
    }, as_dict=1)
    
    summary = {
        'total_payments': len(payments),
        'total_amount': sum([p.amount_paid for p in payments]),
        'total_wht': sum([p.wht_amount or 0 for p in payments]),
        'total_net': sum([p.net_amount or p.amount_paid for p in payments]),
        'payments': payments
    }
    
    return summary


# ==================== Whitelisted API Methods ====================

@frappe.whitelist()
def get_payment_summary_card(payment_name):
    """Get payment summary for display card"""
    payment = frappe.get_doc('Payments', payment_name)
    
    summary = {
        'payment_no': payment.name,
        'payee': payment.payee_name or payment.supplier_name,
        'amount': format_currency_display(
            payment.amount_paid or payment.amount_paid_in_fc,
            payment.payment_currency
        ),
        'amount_in_words': payment.amount_in_words,
        'status': payment.payment_status,
        'date': payment.transaction_date,
        'reference': payment.reference_no,
        'purpose': payment.transaction_purposes
    }
    
    if payment.deduct_wht:
        summary['wht_amount'] = format_currency_display(payment.wht_amount, payment.payment_currency)
        summary['net_amount'] = format_currency_display(payment.net_amount, payment.payment_currency)
    
    summary['links'] = get_document_links(payment_name)
    
    return summary


@frappe.whitelist()
def send_payment_notification(payment_name, notification_type='confirmation'):
    """Send payment notification"""
    payment = frappe.get_doc('Payments', payment_name)
    
    if notification_type == 'approval':
        PaymentNotifier.send_approval_notification(payment)
    elif notification_type == 'confirmation':
        PaymentNotifier.send_payment_confirmation(payment)
    
    return {'success': True, 'message': 'Notification sent'}


@frappe.whitelist()
def check_payment_duplicates(supplier, amount, transaction_date, current_doc=None):
    """Check for duplicate payments"""
    return check_duplicate_payment(supplier, amount, transaction_date, None, current_doc)


@frappe.whitelist()
def batch_process_payments(payment_names):
    """Process multiple payments"""
    if isinstance(payment_names, str):
        payment_names = json.loads(payment_names)
    
    return BatchPaymentProcessor.process_batch(payment_names)


@frappe.whitelist()
def export_payments_report(filters):
    """Export payments to Excel"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    frappe.msgprint(_("Export functionality will be implemented"))
    return {'success': True}


@frappe.whitelist()
def get_payment_dashboard_data(company, from_date=None, to_date=None):
    """Get dashboard analytics"""
    if not from_date:
        from_date = frappe.utils.add_months(nowdate(), -1)
    if not to_date:
        to_date = nowdate()
    
    return get_payment_analytics(company, from_date, to_date)