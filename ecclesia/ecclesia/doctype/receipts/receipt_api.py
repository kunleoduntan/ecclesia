# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# Path: general_biz_apps/general_biz_apps/doctype/receipts/receipt_api.py
# Receipt API Helper Functions

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate
import json


@frappe.whitelist()
def apply_receipt_to_invoice(receipt_no, invoice_no, amount):
    """Apply receipt to invoice"""
    try:
        amount = flt(amount)
        
        # Validate receipt
        receipt = frappe.get_doc("Receipts", receipt_no)
        if receipt.docstatus != 1:
            frappe.throw(_("Receipt must be submitted"))
        
        # Validate invoice
        invoice = frappe.get_doc("Sales Invoice", invoice_no)
        if invoice.docstatus != 1:
            frappe.throw(_("Invoice must be submitted"))
        
        if invoice.outstanding_amount <= 0:
            frappe.throw(_("Invoice has no outstanding amount"))
        
        # Validate amount
        if amount <= 0:
            frappe.throw(_("Amount must be greater than zero"))
        
        if amount > invoice.outstanding_amount:
            frappe.throw(_("Amount cannot exceed invoice outstanding amount"))
        
        # Get current applied amount for this receipt
        current_applied = frappe.db.sql("""
            SELECT COALESCE(SUM(amount_applied), 0) as total
            FROM `tabReceipt Allocation`
            WHERE parent = %s
        """, receipt_no)[0][0]
        
        receipt_amount = receipt.amount_received or receipt.amount_received_in_fc or 0
        
        if (current_applied + amount) > receipt_amount:
            frappe.throw(_("Total applied amount cannot exceed receipt amount"))
        
        # Create allocation
        allocation = frappe.get_doc({
            "doctype": "Receipt Allocation",
            "parent": receipt_no,
            "parenttype": "Receipts",
            "parentfield": "allocations",
            "invoice_number": invoice_no,
            "outstanding_amount": invoice.outstanding_amount,
            "amount_applied": amount,
            "allocation_date": nowdate()
        })
        allocation.insert(ignore_permissions=True)
        
        # Update invoice outstanding
        new_outstanding = invoice.outstanding_amount - amount
        frappe.db.set_value("Sales Invoice", invoice_no, "outstanding_amount", new_outstanding)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Receipt applied successfully"),
            "allocation": allocation.name
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Receipt Application Error"))
        frappe.throw(_("Error applying receipt: {0}").format(str(e)))


@frappe.whitelist()
def send_payment_reminders(customers):
    """Send payment reminders to customers"""
    
    if isinstance(customers, str):
        customers = json.loads(customers)
    
    sent_count = 0
    errors = []
    
    for customer_id in customers:
        try:
            customer = frappe.get_doc("Customer", customer_id)
            
            # Get outstanding invoices
            invoices = frappe.get_all("Sales Invoice",
                filters={
                    "customer": customer_id,
                    "docstatus": 1,
                    "outstanding_amount": [">", 0]
                },
                fields=["name", "posting_date", "due_date", "outstanding_amount"]
            )
            
            if not invoices:
                continue
            
            # Send email
            send_reminder_email(customer, invoices)
            sent_count += 1
            
        except Exception as e:
            errors.append(f"{customer_id}: {str(e)}")
            frappe.log_error(frappe.get_traceback(), f"Payment Reminder Error - {customer_id}")
    
    return {
        "success": True,
        "sent_count": sent_count,
        "errors": errors
    }


def send_reminder_email(customer, invoices):
    """Send payment reminder email to customer"""
    
    if not customer.email_id:
        frappe.throw(_("Customer {0} has no email address").format(customer.name))
    
    # Build invoice table
    invoice_rows = ""
    total_outstanding = 0
    
    for inv in invoices:
        invoice_rows += f"""
        <tr>
            <td>{inv.name}</td>
            <td>{inv.posting_date}</td>
            <td>{inv.due_date}</td>
            <td style="text-align: right;">{frappe.utils.fmt_money(inv.outstanding_amount)}</td>
        </tr>
        """
        total_outstanding += inv.outstanding_amount
    
    message = f"""
    <p>Dear {customer.customer_name},</p>
    
    <p>This is a friendly reminder regarding your outstanding invoices with us.</p>
    
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <thead>
            <tr style="background-color: #f2f2f2;">
                <th>Invoice No</th>
                <th>Invoice Date</th>
                <th>Due Date</th>
                <th>Outstanding Amount</th>
            </tr>
        </thead>
        <tbody>
            {invoice_rows}
        </tbody>
        <tfoot>
            <tr style="font-weight: bold; background-color: #f2f2f2;">
                <td colspan="3" style="text-align: right;">Total Outstanding:</td>
                <td style="text-align: right;">{frappe.utils.fmt_money(total_outstanding)}</td>
            </tr>
        </tfoot>
    </table>
    
    <p>Please arrange for payment at your earliest convenience.</p>
    
    <p>If you have already made the payment, please disregard this reminder.</p>
    
    <p>Best regards,<br>
    {frappe.get_value("Company", frappe.defaults.get_user_default("Company"), "company_name")}</p>
    """
    
    frappe.sendmail(
        recipients=[customer.email_id],
        subject=f"Payment Reminder - Outstanding Invoices",
        message=message,
        delayed=False
    )


@frappe.whitelist()
def get_receipt_statistics(company, from_date, to_date):
    """Get receipt statistics for dashboard"""
    
    stats = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_receipts,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as total_amount,
            AVG(COALESCE(amount_received, amount_received_in_fc, 0)) as avg_amount,
            SUM(CASE WHEN receipt_status = 'Cleared' THEN 1 ELSE 0 END) as cleared_count,
            SUM(CASE WHEN receipt_status = 'Pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN receipt_status = 'Bounced' THEN 1 ELSE 0 END) as bounced_count,
            SUM(COALESCE(wht_amount, 0)) as total_wht
        FROM `tabReceipts`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
    """, (company, from_date, to_date), as_dict=1)
    
    return stats[0] if stats else {}


@frappe.whitelist()
def export_receipts_to_excel(filters):
    """Export receipts to Excel"""
    from frappe.utils.xlsxutils import make_xlsx
    
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    # Get data
    from general_biz_apps.general_biz_apps.report.receipt_register.receipt_register import (
        get_columns, get_data
    )
    
    columns = get_columns()
    data = get_data(filters)
    
    # Prepare data for Excel
    xlsx_data = []
    
    # Add headers
    headers = [col.get("label") for col in columns]
    xlsx_data.append(headers)
    
    # Add data rows
    for row in data:
        xlsx_row = []
        for col in columns:
            xlsx_row.append(row.get(col.get("fieldname"), ""))
        xlsx_data.append(xlsx_row)
    
    # Generate Excel file
    xlsx_file = make_xlsx(xlsx_data, "Receipt Register")
    
    frappe.response['filename'] = 'receipt_register.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'


@frappe.whitelist()
def bulk_update_receipt_status(receipts, new_status):
    """Bulk update receipt status"""
    
    if isinstance(receipts, str):
        receipts = json.loads(receipts)
    
    valid_statuses = ["Pending", "Cleared", "Bounced", "Cancelled"]
    if new_status not in valid_statuses:
        frappe.throw(_("Invalid status"))
    
    updated_count = 0
    errors = []
    
    for receipt_no in receipts:
        try:
            frappe.db.set_value("Receipts", receipt_no, "receipt_status", new_status)
            updated_count += 1
        except Exception as e:
            errors.append(f"{receipt_no}: {str(e)}")
    
    frappe.db.commit()
    
    return {
        "success": True,
        "updated_count": updated_count,
        "errors": errors
    }


@frappe.whitelist()
def get_customer_receipt_history(customer_id, limit=10):
    """Get recent receipt history for a customer"""
    
    receipts = frappe.get_all("Receipts",
        filters={
            "customer_id": customer_id,
            "docstatus": 1
        },
        fields=[
            "name",
            "transaction_date",
            "amount_received",
            "receipt_currency",
            "mode_of_payment",
            "receipt_status"
        ],
        order_by="transaction_date desc",
        limit=limit
    )
    
    return receipts


@frappe.whitelist()
def validate_receipt_allocation(receipt_no):
    """Validate receipt allocation before submission"""
    
    receipt = frappe.get_doc("Receipts", receipt_no)
    
    errors = []
    warnings = []
    
    # Check if receipt amount matches allocations
    total_allocated = sum(
        flt(alloc.amount_applied) 
        for alloc in receipt.get("allocations", [])
    )
    
    receipt_amount = receipt.amount_received or receipt.amount_received_in_fc or 0
    
    if total_allocated > receipt_amount:
        errors.append(_("Total allocated amount exceeds receipt amount"))
    
    if total_allocated < receipt_amount:
        warnings.append(
            _("Receipt has unapplied amount of {0}").format(
                frappe.utils.fmt_money(receipt_amount - total_allocated)
            )
        )
    
    # Validate each allocation
    for alloc in receipt.get("allocations", []):
        invoice = frappe.get_doc("Sales Invoice", alloc.invoice_number)
        
        if invoice.outstanding_amount < alloc.amount_applied:
            errors.append(
                _("Allocation for {0} exceeds outstanding amount").format(alloc.invoice_number)
            )
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


@frappe.whitelist()
def get_unapplied_receipts(company, customer_id=None):
    """Get receipts with unapplied amounts"""
    
    conditions = "r.company = %(company)s AND r.docstatus = 1"
    values = {"company": company}
    
    if customer_id:
        conditions += " AND r.customer_id = %(customer_id)s"
        values["customer_id"] = customer_id
    
    data = frappe.db.sql(f"""
        SELECT 
            r.name,
            r.transaction_date,
            r.customer_id,
            COALESCE(r.customer_name, r.payer_name) as customer_name,
            COALESCE(r.amount_received, r.amount_received_in_fc, 0) as receipt_amount,
            COALESCE(SUM(ra.amount_applied), 0) as applied_amount,
            COALESCE(r.amount_received, r.amount_received_in_fc, 0) - COALESCE(SUM(ra.amount_applied), 0) as unapplied_amount
        FROM `tabReceipts` r
        LEFT JOIN `tabReceipt Allocation` ra ON ra.parent = r.name
        WHERE {conditions}
        GROUP BY r.name
        HAVING unapplied_amount > 0
        ORDER BY r.transaction_date DESC
    """, values, as_dict=1)
    
    return data


@frappe.whitelist()
def auto_apply_receipts(customer_id):
    """Automatically apply receipts to oldest invoices for a customer"""
    
    # Get unapplied receipts
    receipts = get_unapplied_receipts(None, customer_id)
    
    if not receipts:
        return {
            "success": True,
            "message": _("No unapplied receipts found"),
            "applied_count": 0
        }
    
    # Get outstanding invoices
    invoices = frappe.get_all("Sales Invoice",
        filters={
            "customer": customer_id,
            "docstatus": 1,
            "outstanding_amount": [">", 0]
        },
        fields=["name", "outstanding_amount", "due_date"],
        order_by="due_date asc"
    )
    
    if not invoices:
        return {
            "success": True,
            "message": _("No outstanding invoices found"),
            "applied_count": 0
        }
    
    applied_count = 0
    
    # Apply receipts to invoices
    for receipt in receipts:
        remaining_amount = receipt.unapplied_amount
        
        for invoice in invoices:
            if remaining_amount <= 0:
                break
            
            if invoice.outstanding_amount <= 0:
                continue
            
            # Apply amount
            apply_amount = min(remaining_amount, invoice.outstanding_amount)
            
            try:
                result = apply_receipt_to_invoice(
                    receipt.name,
                    invoice.name,
                    apply_amount
                )
                
                if result.get("success"):
                    applied_count += 1
                    remaining_amount -= apply_amount
                    invoice.outstanding_amount -= apply_amount
                    
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Auto Apply Error - {receipt.name}")
                continue
    
    return {
        "success": True,
        "message": _("Auto-applied {0} receipt allocations").format(applied_count),
        "applied_count": applied_count
    }