# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days
import json


def execute(filters=None):
    """Main report execution function"""
    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data


def get_columns(filters):
    """Define report columns"""
    columns = [
        {
            "label": _("Date"),
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Receipt No"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Receipts",
            "width": 150
        },
        {
            "label": _("Customer"),
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Customer ID"),
            "fieldname": "customer_id",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 120
        },
        {
            "label": _("Transaction Type"),
            "fieldname": "trans_type",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("Reference No"),
            "fieldname": "reference_no",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Amount"),
            "fieldname": "amount_received",
            "fieldtype": "Currency",
            "options": "receipt_currency",
            "width": 130
        },
        {
            "label": _("Currency"),
            "fieldname": "receipt_currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80
        },
        {
            "label": _("Local Amount"),
            "fieldname": "local_currency_amount",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Payment Mode"),
            "fieldname": "mode_of_payment",
            "fieldtype": "Link",
            "options": "Mode of Payment",
            "width": 130
        },
        {
            "label": _("Bank Account"),
            "fieldname": "remittance_bank",
            "fieldtype": "Link",
            "options": "Bank Account",
            "width": 160
        },
        {
            "label": _("Status"),
            "fieldname": "receipt_status",
            "fieldtype": "Data",
            "width": 110
        },
        {
            "label": _("Remarks"),
            "fieldname": "transaction_purposes",
            "fieldtype": "Text",
            "width": 200
        }
    ]
    
    return columns


def get_data(filters):
    """Fetch receipt data based on filters"""
    conditions = get_conditions(filters)
    
    query = """
        SELECT
            r.transaction_date,
            r.name,
            r.customer_name,
            r.payer_name,
            r.customer_id,
            r.trans_type,
            r.reference_no,
            r.amount_received,
            r.amount_received_in_fc,
            r.receipt_currency,
            r.local_currency_amount,
            r.exchange_rate,
            r.mode_of_payment,
            r.remittance_bank,
            r.receipt_status,
            r.transaction_purposes,
            r.company,
            r.docstatus
        FROM `tabReceipts` r
        WHERE r.docstatus IN (0, 1)
        {conditions}
        ORDER BY r.transaction_date DESC, r.name DESC
    """.format(conditions=conditions)
    
    data = frappe.db.sql(query, filters, as_dict=1)
    
    # Post-process data
    for row in data:
        # Use customer_name or payer_name
        if not row.customer_name:
            row.customer_name = row.payer_name or ""
        
        # Calculate local currency amount if not set
        if not row.local_currency_amount:
            if row.receipt_currency and row.receipt_currency != frappe.db.get_value('Company', filters.get('company'), 'default_currency'):
                row.local_currency_amount = (row.amount_received_in_fc or 0) * (row.exchange_rate or 1)
            else:
                row.local_currency_amount = row.amount_received or 0
        
        # Use appropriate amount field
        if not row.amount_received and row.amount_received_in_fc:
            row.amount_received = row.amount_received_in_fc
    
    return data


def get_conditions(filters):
    """Build SQL conditions from filters"""
    conditions = []
    
    if filters.get("company"):
        conditions.append("r.company = %(company)s")
    
    if filters.get("from_date"):
        conditions.append("r.transaction_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("r.transaction_date <= %(to_date)s")
    
    if filters.get("customer_id"):
        conditions.append("r.customer_id = %(customer_id)s")
    
    if filters.get("trans_type"):
        conditions.append("r.trans_type = %(trans_type)s")
    
    if filters.get("mode_of_payment"):
        conditions.append("r.mode_of_payment = %(mode_of_payment)s")
    
    if filters.get("receipt_status"):
        conditions.append("r.receipt_status = %(receipt_status)s")
    
    if filters.get("remittance_bank"):
        conditions.append("r.remittance_bank = %(remittance_bank)s")
    
    if filters.get("receipt_currency"):
        conditions.append("r.receipt_currency = %(receipt_currency)s")
    
    if filters.get("min_amount"):
        conditions.append("r.local_currency_amount >= %(min_amount)s")
    
    if filters.get("max_amount"):
        conditions.append("r.local_currency_amount <= %(max_amount)s")
    
    return " AND " + " AND ".join(conditions) if conditions else ""


@frappe.whitelist()
def export_to_excel(filters):
    """Export report data to Excel"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    from frappe.utils.xlsxutils import make_xlsx
    
    columns, data = execute(filters)
    
    # Prepare data for Excel
    excel_data = []
    
    # Add headers
    headers = [col.get("label") for col in columns]
    excel_data.append(headers)
    
    # Add data rows
    for row in data:
        excel_row = []
        for col in columns:
            fieldname = col.get("fieldname")
            value = row.get(fieldname, "")
            
            # Format currency values
            if col.get("fieldtype") == "Currency":
                value = flt(value, 2)
            
            excel_row.append(value)
        excel_data.append(excel_row)
    
    # Create Excel file
    xlsx_file = make_xlsx(excel_data, "Receipt Register")
    
    # Save to public folder
    file_name = f"Receipt_Register_{nowdate()}.xlsx"
    file_path = f"/files/{file_name}"
    
    with open(frappe.get_site_path('public', 'files', file_name), 'wb') as f:
        f.write(xlsx_file.getvalue())
    
    return file_path


@frappe.whitelist()
def send_email_report(filters, recipients, subject, message, attach_excel=1):
    """Send report via email"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    # Get report data
    columns, data = execute(filters)
    
    # Generate HTML table
    html_table = generate_html_table(columns, data, filters)
    
    # Prepare email message
    email_message = f"""
        <div style="font-family: Arial, sans-serif;">
            <p>{message}</p>
            <br>
            {html_table}
        </div>
    """
    
    # Prepare attachments
    attachments = []
    if int(attach_excel):
        excel_path = export_to_excel(filters)
        file_path = frappe.get_site_path('public', excel_path.lstrip('/'))
        
        with open(file_path, 'rb') as f:
            attachments.append({
                'fname': f"Receipt_Register_{nowdate()}.xlsx",
                'fcontent': f.read()
            })
    
    # Send email
    recipient_list = [email.strip() for email in recipients.split(',')]
    
    frappe.sendmail(
        recipients=recipient_list,
        subject=subject,
        message=email_message,
        attachments=attachments,
        now=True
    )
    
    return {"status": "success", "message": "Email sent successfully"}


def generate_html_table(columns, data, filters):
    """Generate HTML table for email"""
    # Calculate totals
    total_amount = sum(flt(row.get('local_currency_amount', 0)) for row in data)
    
    # Build HTML
    html = f"""
        <div style="margin: 20px 0;">
            <h3 style="color: #333; border-bottom: 2px solid #2196f3; padding-bottom: 10px;">
                Receipt Register Report
            </h3>
            <div style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
                <strong>Period:</strong> {filters.get('from_date')} to {filters.get('to_date')}<br>
                <strong>Company:</strong> {filters.get('company')}<br>
                <strong>Total Receipts:</strong> {len(data)}<br>
                <strong>Total Amount:</strong> {frappe.utils.fmt_money(total_amount, currency=frappe.db.get_value('Company', filters.get('company'), 'default_currency'))}
            </div>
            
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead>
                    <tr style="background: #2196f3; color: white;">
                        <th style="padding: 10px; text-align: left; border: 1px solid #1976d2;">Date</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #1976d2;">Receipt No</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #1976d2;">Customer</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #1976d2;">Reference</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #1976d2;">Amount</th>
                        <th style="padding: 10px; text-align: center; border: 1px solid #1976d2;">Status</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for i, row in enumerate(data):
        bg_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        html += f"""
            <tr style="background: {bg_color};">
                <td style="padding: 8px; border: 1px solid #ddd;">{row.get('transaction_date', '')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row.get('name', '')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row.get('customer_name', '')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row.get('reference_no', '')}</td>
                <td style="padding: 8px; text-align: right; border: 1px solid #ddd; font-weight: bold;">
                    {frappe.utils.fmt_money(row.get('local_currency_amount', 0))}
                </td>
                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">{row.get('receipt_status', '')}</td>
            </tr>
        """
    
    html += f"""
                </tbody>
                <tfoot>
                    <tr style="background: #e3f2fd; font-weight: bold;">
                        <td colspan="4" style="padding: 10px; border: 1px solid #ddd; text-align: right;">TOTAL</td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">
                            {frappe.utils.fmt_money(total_amount)}
                        </td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{len(data)} Receipts</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    """
    
    return html