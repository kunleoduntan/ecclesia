# -*- coding: utf-8 -*-
# Copyright (c) 2026, Value Impacts Consulting
# For license information, please see license.txt

"""
Purchase Invoice API Module
File: ecclesia/api/purchase_invoice.py

Features:
- Automated amortization journal entries
- Cost center distribution support
- Beautiful HTML print formats
- Transaction validation
"""

import frappe
import json
from frappe import _
from frappe.utils import getdate, flt, add_months, format_date, nowdate, cint

# ============================================================================
# DOCUMENT HOOKS (Setup via hooks.py)
# ============================================================================

def purchase_invoice_validate(doc, method):
    """Validate Purchase Invoice on save"""
    
    # Validate amortization
    if doc.custom_is_amortized_cost:
        validate_amortization(doc)
        calculate_amortization_schedule(doc)
    
    # Validate cost center distribution
    if doc.custom_is_shared_cost and doc.custom_cost_center_distribution:
        validate_cost_center_distribution(doc)
    
    # Calculate transaction balances
    if doc.custom_transaction_history:
        calculate_transaction_balances(doc)


def purchase_invoice_on_submit(doc, method):
    """On submit actions"""
    pass


def purchase_invoice_on_cancel(doc, method):
    """On cancel - delete related journal entries"""
    if doc.custom_is_amortized_cost:
        delete_related_journal_entries(doc)


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_amortization(doc):
    """Validate amortization settings"""
    
    if not doc.custom_frequency:
        frappe.throw(_("Frequency is required for amortization"))
    
    if not doc.custom_start_date:
        frappe.throw(_("Start Date is required for amortization"))
    
    if not doc.custom_expense_account:
        frappe.throw(_("Expense Account is required for amortization"))
    
    if not doc.custom_deferred_expense_account:
        frappe.throw(_("Deferred Expense Account is required for amortization"))
    
    # Validate accounts are not group accounts
    validate_account(doc.custom_expense_account, "Expense Account")
    validate_account(doc.custom_deferred_expense_account, "Deferred Expense Account")
    
    # Ensure cost center is set (if not using shared cost)
    if not doc.cost_center and not doc.custom_is_shared_cost:
        frappe.throw(_("Cost Center is required for amortization"))


def validate_account(account, label):
    """Validate account is not a group account"""
    if not account:
        return
    
    is_group = frappe.db.get_value("Account", account, "is_group")
    if is_group:
        frappe.throw(_(
            "The account {0} ({1}) is a group account and cannot be used for posting"
        ).format(account, label))


def validate_cost_center_distribution(doc):
    """Validate cost center distribution totals 100%"""
    
    if not doc.custom_cost_center_distribution:
        return
    
    total_percentage = sum([flt(row.distribution) for row in doc.custom_cost_center_distribution])
    
    if abs(total_percentage - 100) > 0.01:
        frappe.throw(_(
            "Total cost center distribution must equal 100%. Current total: {0}%"
        ).format(total_percentage))


# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_amortization_schedule(doc):
    """Calculate and populate amortization schedule"""
    
    if not doc.custom_is_amortized_cost:
        return
    
    if not doc.custom_charged_amount or not doc.custom_no_of_periods:
        return
    
    # Clear existing schedule
    doc.custom_amortization_schedule = []
    
    periods = cint(doc.custom_no_of_periods)
    amount_per_period = flt(doc.custom_charged_amount)
    total_amount = amount_per_period * periods
    remaining_balance = total_amount
    
    for i in range(periods):
        # Calculate posting date
        posting_date = add_months(getdate(doc.custom_start_date), i * cint(doc.custom_next_schedule or 1))
        
        remaining_balance -= amount_per_period
        
        # Add schedule row
        doc.append("custom_amortization_schedule", {
            "date": posting_date,
            "title": doc.supplier_name,
            "amount": amount_per_period,
            "transaction_description": doc.custom_description or "",
            "frequency": doc.custom_frequency,
            "period": periods,
            "account_to_debit": doc.custom_expense_account,
            "account_to_credit": doc.custom_deferred_expense_account,
            "source_doc": "Purchase Invoice",
            "source_doc_ref": doc.name,
            "prepayment_balance": remaining_balance if remaining_balance > 0 else 0
        })


def calculate_transaction_balances(doc):
    """Calculate running balances in transaction history"""
    
    if not doc.custom_transaction_history:
        return
    
    balance = flt(doc.custom_opening_balance)
    total_purchase = 0
    total_paid = 0
    
    for row in doc.custom_transaction_history:
        total_purchase += flt(row.invoice_amount)
        total_paid += flt(row.paid_amount)
        balance += flt(row.invoice_amount) - flt(row.paid_amount)
        row.balance = balance
    
    doc.cum_paid_amount = total_paid
    doc.total_purchases = total_purchase
    doc.balance = balance


# ============================================================================
# AMORTIZATION JOURNAL ENTRY CREATION
# ============================================================================

@frappe.whitelist()
def create_amortization_entries(purchase_invoice):
    """
    Create amortization journal entries for Purchase Invoice
    Supports both single cost center and multi-cost center distribution
    
    Args:
        purchase_invoice: Name of the Purchase Invoice
    """
    
    try:
        # Get document
        doc = frappe.get_doc('Purchase Invoice', purchase_invoice)
        
        # Validation
        if not doc.custom_is_amortized_cost:
            frappe.throw(_("This invoice is not marked for amortization"))
        
        if doc.docstatus != 1:
            frappe.throw(_("Please submit the invoice before creating amortization entries"))
        
        # Check for duplicate entries
        existing_entries = frappe.get_all("Journal Entry", 
            filters={
                "reference_document_no": doc.name,
                "docstatus": ["!=", 2]
            },
            limit=1
        )
        
        if existing_entries:
            frappe.throw(_("Amortization entries already exist for {0}").format(doc.name))
        
        # Validate accounts
        validate_account(doc.custom_expense_account, "Expense Account")
        validate_account(doc.custom_deferred_expense_account, "Deferred Expense Account")
        
        # Create entries based on cost sharing
        if doc.custom_is_shared_cost and doc.custom_cost_center_distribution:
            entries_created = create_shared_cost_entries(doc)
        else:
            entries_created = create_single_cost_entries(doc)
        
        return {
            'success': True,
            'message': f'{entries_created} amortization entries created',
            'entries_created': entries_created
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Amortization Error")
        frappe.throw(_("Error creating amortization entries: {0}").format(str(e)))


def create_single_cost_entries(doc):
    """Create amortization entries for single cost center"""
    
    if not doc.cost_center:
        frappe.throw(_("Cost Center is required for amortization"))
    
    entries_created = 0
    
    for i in range(cint(doc.custom_no_of_periods)):
        # Calculate posting date
        posting_date = add_months(getdate(doc.custom_start_date), i * cint(doc.custom_next_schedule or 1))
        
        # Create journal entry
        journal_entry = create_journal_entry_base(doc, posting_date, i + 1)
        
        # Add debit entry
        journal_entry.append("accounts", {
            "account": doc.custom_expense_account,
            "debit_in_account_currency": flt(doc.custom_charged_amount),
            "cost_center": doc.cost_center,
            "user_remark": doc.custom_description or "",
            "against_account": doc.custom_deferred_expense_account
        })
        
        # Add credit entry
        journal_entry.append("accounts", {
            "account": doc.custom_deferred_expense_account,
            "credit_in_account_currency": flt(doc.custom_charged_amount),
            "user_remark": doc.custom_description or "",
            "against_account": doc.custom_expense_account
        })
        
        # Save journal entry
        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()
        frappe.db.commit()
        entries_created += 1
    
    return entries_created


def create_shared_cost_entries(doc):
    """Create amortization entries with cost center distribution"""
    
    # Validate distribution
    total_percentage = sum([flt(row.distribution) for row in doc.custom_cost_center_distribution])
    if abs(total_percentage - 100) > 0.01:
        frappe.throw(_("Total cost center distribution must equal 100%. Current: {0}%").format(total_percentage))
    
    entries_created = 0
    
    for i in range(cint(doc.custom_no_of_periods)):
        # Calculate posting date
        posting_date = add_months(getdate(doc.custom_start_date), i * cint(doc.custom_next_schedule or 1))
        
        # Create journal entry
        journal_entry = create_journal_entry_base(doc, posting_date, i + 1)
        
        # Add debit entries for each cost center
        for cc_row in doc.custom_cost_center_distribution:
            amount_to_debit = flt(doc.custom_charged_amount * (flt(cc_row.distribution) / 100.0))
            
            journal_entry.append("accounts", {
                "account": doc.custom_expense_account,
                "debit_in_account_currency": amount_to_debit,
                "cost_center": cc_row.cost_center,
                "user_remark": f"{doc.custom_description or ''} - {cc_row.title or ''} ({cc_row.distribution}%)",
                "against_account": doc.custom_deferred_expense_account
            })
        
        # Add credit entry
        journal_entry.append("accounts", {
            "account": doc.custom_deferred_expense_account,
            "credit_in_account_currency": flt(doc.custom_charged_amount),
            "user_remark": doc.custom_description or "",
            "against_account": doc.custom_expense_account
        })
        
        # Save journal entry
        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()
        frappe.db.commit()
        entries_created += 1
    
    return entries_created


def create_journal_entry_base(doc, posting_date, period_number):
    """Create base journal entry object"""
    
    journal_entry = frappe.new_doc("Journal Entry")
    journal_entry.voucher_type = "Journal Entry"
    journal_entry.company = doc.company
    journal_entry.posting_date = posting_date
    journal_entry.user_remark = f"Amortization entry for {doc.name} - Period {period_number}/{doc.custom_no_of_periods}"
    journal_entry.reference_document_no = doc.name
    
    # Add custom fields if they exist
    if hasattr(journal_entry, 'custom_reference_doctype'):
        journal_entry.custom_reference_doctype = "Purchase Invoice"
    
    return journal_entry


def delete_related_journal_entries(doc):
    """Delete related journal entries when invoice is cancelled"""
    
    related_entries = frappe.get_all("Journal Entry",
        filters={
            "reference_document_no": doc.name,
            "docstatus": ["!=", 2]
        },
        pluck="name"
    )
    
    for entry_name in related_entries:
        try:
            je = frappe.get_doc("Journal Entry", entry_name)
            if je.docstatus == 1:
                je.cancel()
            frappe.delete_doc("Journal Entry", entry_name, force=1)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Error deleting Journal Entry {entry_name}")


# ============================================================================
# HTML PRINT FORMATS
# ============================================================================

@frappe.whitelist()
def generate_amortization_html(purchase_invoice):
    """Generate beautiful HTML print for amortization schedule"""
    
    doc = frappe.get_doc('Purchase Invoice', purchase_invoice)
    
    if not doc.custom_amortization_schedule:
        frappe.throw(_("No amortization schedule found"))
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Amortization Schedule - {doc.name}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px;
                color: white;
                text-align: center;
            }}
            .header h1 {{
                font-size: 36px;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }}
            .info-section {{
                padding: 30px;
                background: #f8f9fa;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
            }}
            .info-item {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .info-label {{
                color: #7f8c8d;
                font-size: 12px;
                text-transform: uppercase;
                margin-bottom: 5px;
            }}
            .info-value {{
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
            }}
            .schedule-section {{
                padding: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            th {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px;
                text-align: left;
                font-weight: 600;
                font-size: 13px;
                text-transform: uppercase;
            }}
            td {{
                padding: 12px 15px;
                border-bottom: 1px solid #ecf0f1;
            }}
            tr:hover {{
                background: #f8f9fa;
            }}
            tr:nth-child(even) {{
                background: #f8f9fa;
            }}
            .amount {{
                text-align: right;
                font-weight: bold;
            }}
            .total-row {{
                background: #667eea !important;
                color: white;
                font-weight: bold;
            }}
            .footer {{
                background: #2c3e50;
                color: white;
                padding: 20px;
                text-align: center;
            }}
            @media print {{
                body {{ background: white; padding: 0; }}
                .container {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Amortization Schedule</h1>
                <p>{doc.supplier_name}</p>
                <p>Invoice: {doc.name}</p>
            </div>
            
            <div class="info-section">
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Total Amount</div>
                        <div class="info-value">{frappe.utils.fmt_money(doc.base_total, currency=doc.currency)}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Frequency</div>
                        <div class="info-value">{doc.custom_frequency}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Number of Periods</div>
                        <div class="info-value">{doc.custom_no_of_periods}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Amount Per Period</div>
                        <div class="info-value">{frappe.utils.fmt_money(doc.custom_charged_amount, currency=doc.currency)}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Start Date</div>
                        <div class="info-value">{format_date(doc.custom_start_date)}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">End Date</div>
                        <div class="info-value">{format_date(doc.custom_end_date)}</div>
                    </div>
                </div>
            </div>
            
            <div class="schedule-section">
                <h2 style="margin-bottom: 20px; color: #2c3e50;">📅 Payment Schedule</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Period</th>
                            <th>Date</th>
                            <th>Description</th>
                            <th class="amount">Amount</th>
                            <th class="amount">Remaining Balance</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Add schedule rows
    total_amount = 0
    for idx, row in enumerate(doc.custom_amortization_schedule, 1):
        total_amount += flt(row.amount)
        html += f"""
                        <tr>
                            <td>{idx}</td>
                            <td>{format_date(row.date)}</td>
                            <td>{row.transaction_description or ''}</td>
                            <td class="amount">{frappe.utils.fmt_money(row.amount, currency=doc.currency)}</td>
                            <td class="amount">{frappe.utils.fmt_money(row.prepayment_balance, currency=doc.currency)}</td>
                        </tr>
        """
    
    # Add total row
    html += f"""
                        <tr class="total-row">
                            <td colspan="3">TOTAL</td>
                            <td class="amount">{frappe.utils.fmt_money(total_amount, currency=doc.currency)}</td>
                            <td class="amount">0.00</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>Generated on {format_date(nowdate())} | {frappe.db.get_value('Company', doc.company, 'company_name')}</p>
                <p>Debit: {doc.custom_expense_account} | Credit: {doc.custom_deferred_expense_account}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


@frappe.whitelist()
def generate_cost_sharing_html(purchase_invoice):
    """Generate beautiful HTML print for cost center sharing"""
    
    doc = frappe.get_doc('Purchase Invoice', purchase_invoice)
    
    if not doc.custom_cost_center_distribution:
        frappe.throw(_("No cost center distribution found"))
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Cost Sharing Analysis - {doc.name}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #FF9A9E 0%, #FAD0C4 100%);
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .header {{
                background: linear-gradient(135deg, #FF9A9E 0%, #FAD0C4 100%);
                padding: 40px;
                color: white;
                text-align: center;
            }}
            .header h1 {{
                font-size: 36px;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }}
            .summary-section {{
                padding: 30px;
                background: #f8f9fa;
            }}
            .summary-card {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .summary-label {{
                color: #7f8c8d;
                font-size: 14px;
                margin-bottom: 5px;
            }}
            .summary-value {{
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }}
            .distribution-section {{
                padding: 30px;
            }}
            .cc-card {{
                background: white;
                border-left: 5px solid #FF9A9E;
                padding: 20px;
                margin-bottom: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .cc-info {{
                flex: 1;
            }}
            .cc-name {{
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }}
            .cc-title {{
                color: #7f8c8d;
                font-size: 14px;
            }}
            .cc-amount {{
                text-align: right;
            }}
            .cc-percentage {{
                font-size: 24px;
                font-weight: bold;
                color: #FF9A9E;
                margin-bottom: 5px;
            }}
            .cc-money {{
                font-size: 16px;
                color: #2c3e50;
            }}
            .chart-section {{
                padding: 30px;
                background: #f8f9fa;
            }}
            .bar-chart {{
                margin-top: 20px;
            }}
            .bar-item {{
                margin-bottom: 15px;
            }}
            .bar-label {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 5px;
                font-size: 14px;
            }}
            .bar {{
                height: 30px;
                background: linear-gradient(90deg, #FF9A9E 0%, #FAD0C4 100%);
                border-radius: 15px;
                position: relative;
            }}
            .footer {{
                background: #2c3e50;
                color: white;
                padding: 20px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💰 Cost Sharing Analysis</h1>
                <p>{doc.supplier_name}</p>
                <p>Invoice: {doc.name}</p>
            </div>
            
            <div class="summary-section">
                <div class="summary-card">
                    <div class="summary-label">Total Invoice Amount</div>
                    <div class="summary-value">{frappe.utils.fmt_money(doc.base_total, currency=doc.currency)}</div>
                </div>
                <div class="summary-card">
                    <div class="summary-label">Amount Per Period</div>
                    <div class="summary-value">{frappe.utils.fmt_money(doc.custom_charged_amount, currency=doc.currency)}</div>
                </div>
            </div>
            
            <div class="distribution-section">
                <h2 style="margin-bottom: 20px; color: #2c3e50;">📊 Cost Center Distribution</h2>
    """
    
    # Add cost center cards
    for row in doc.custom_cost_center_distribution:
        amount = flt(doc.custom_charged_amount * (flt(row.distribution) / 100.0))
        html += f"""
                <div class="cc-card">
                    <div class="cc-info">
                        <div class="cc-name">{row.cost_center}</div>
                        <div class="cc-title">{row.title or ''}</div>
                    </div>
                    <div class="cc-amount">
                        <div class="cc-percentage">{row.distribution}%</div>
                        <div class="cc-money">{frappe.utils.fmt_money(amount, currency=doc.currency)}</div>
                    </div>
                </div>
        """
    
    # Add chart section
    html += f"""
            </div>
            
            <div class="chart-section">
                <h2 style="margin-bottom: 20px; color: #2c3e50;">📈 Distribution Breakdown</h2>
                <div class="bar-chart">
    """
    
    # Add bar chart
    for row in doc.custom_cost_center_distribution:
        amount = flt(doc.custom_charged_amount * (flt(row.distribution) / 100.0))
        html += f"""
                    <div class="bar-item">
                        <div class="bar-label">
                            <span>{row.cost_center}</span>
                            <span>{frappe.utils.fmt_money(amount, currency=doc.currency)}</span>
                        </div>
                        <div class="bar" style="width: {row.distribution}%;"></div>
                    </div>
        """
    
    html += f"""
                </div>
            </div>
            
            <div class="footer">
                <p>Generated on {format_date(nowdate())} | {frappe.db.get_value('Company', doc.company, 'company_name')}</p>
                <p>Total Distribution: {doc.custom_total_percentage}%</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html