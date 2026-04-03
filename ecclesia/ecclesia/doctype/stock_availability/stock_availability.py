# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe.model.document import Document
from frappe.utils import flt, fmt_money, get_url_to_form, now_datetime, today, add_days
import json
from datetime import datetime


class StockAvailability(Document):
    def validate(self):
        """Validate document before saving"""
        self.set_title()
        self.calculate_totals()
        self.validate_dates()
    
    def set_title(self):
        """Auto-generate title"""
        if self.warehouse and self.report_date:
            self.title = f"{self.warehouse} - {self.report_date}"
            
            
    def validate_dates(self):
        """Ensure report date is not in the future"""
        if self.report_date:
            # Convert both to date objects for comparison
            report_date = frappe.utils.getdate(self.report_date)
            today_date = frappe.utils.getdate(today())
        
            if report_date > today_date:
                frappe.throw("Report Date cannot be in the future")
    
    def calculate_totals(self):
        """Calculate total amounts"""
        total_value = 0
        total_reorder_value = 0
        
        for row in self.get("stock_balance_entry", []):
            # Calculate amount
            row.amount = flt(row.qty) * flt(row.cost_price)
            
            # Calculate reorder quantity and amount
            if self.criterion == "Reorder Level":
                row.reorder_qty = max(0, flt(row.reorder_level) - flt(row.qty))
            else:
                row.reorder_qty = 0
            
            row.reorder_amount = flt(row.reorder_qty) * flt(row.cost_price)
            
            # Sum totals
            total_value += flt(row.amount)
            total_reorder_value += flt(row.reorder_amount)
        
        self.total = total_value
        self.total_reorder_value = total_reorder_value


@frappe.whitelist()
def fetch_stock_balance(docname):
    """
    Fetch stock balance from Stock Ledger Entry with dynamic field checking
    Returns: dict with status and message
    """
    try:
        doc = frappe.get_doc('Stock Availability', docname)
        
        if not doc.company or not doc.warehouse or not doc.report_date:
            return {
                'status': 'error',
                'message': 'Company, Warehouse, and Report Date are required'
            }
        
        # Get Item doctype fields to check what exists
        item_meta = frappe.get_meta('Item')
        item_fields = [f.fieldname for f in item_meta.fields]
        
        # Get Stock Ledger Entry fields
        sle_meta = frappe.get_meta('Stock Ledger Entry')
        sle_fields = [f.fieldname for f in sle_meta.fields]
        
        # Determine which fields to use for reorder level
        reorder_field_options = [
            'custom_reorder_level', 
            'reorder_level',
            'custom_reorder_qty'
        ]
        
        safety_stock_options = [
            'custom_safety_stock',
            'safety_stock'
        ]
        
        min_order_qty_options = [
            'custom_minimum_order_qty',
            'minimum_order_qty',
            'min_order_qty'
        ]
        
        # Build COALESCE for reorder level
        reorder_coalesce_parts = []
        for field in reorder_field_options:
            if field in sle_fields:
                reorder_coalesce_parts.append(f'sle.{field}')
        reorder_select = f"COALESCE({', '.join(reorder_coalesce_parts)}, 0) as reorder_level" if reorder_coalesce_parts else "0 as reorder_level"
        
        # Build COALESCE for safety stock
        safety_coalesce_parts = []
        for field in safety_stock_options:
            if field in sle_fields:
                safety_coalesce_parts.append(f'sle.{field}')
        safety_select = f"COALESCE({', '.join(safety_coalesce_parts)}, 0) as safety_stock" if safety_coalesce_parts else "0 as safety_stock"
        
        # Build COALESCE for minimum order qty
        min_qty_coalesce_parts = []
        for field in min_order_qty_options:
            if field in sle_fields:
                min_qty_coalesce_parts.append(f'sle.{field}')
        min_qty_select = f"COALESCE({', '.join(min_qty_coalesce_parts)}, 0) as minimum_order_qty" if min_qty_coalesce_parts else "0 as minimum_order_qty"
        
        # Build the query
        query = f"""
            SELECT 
                sle.item_code,
                sle.warehouse,
                sle.stock_uom,
                sle.posting_date,
                sle.qty_after_transaction as qty,
                COALESCE(sle.valuation_rate, sle.outgoing_rate, sle.incoming_rate, 0) as cost_price,
                {reorder_select},
                {safety_select},
                {min_qty_select},
                i.item_name,
                i.item_group,
                sle.creation
            FROM (
                SELECT 
                    item_code,
                    warehouse,
                    MAX(creation) as max_creation
                FROM `tabStock Ledger Entry`
                WHERE 
                    company = %(company)s
                    AND warehouse = %(warehouse)s
                    AND docstatus = 1
                    AND posting_date <= %(report_date)s
                GROUP BY item_code, warehouse
            ) latest
            INNER JOIN `tabStock Ledger Entry` sle 
                ON sle.item_code = latest.item_code 
                AND sle.warehouse = latest.warehouse
                AND sle.creation = latest.max_creation
            LEFT JOIN `tabItem` i ON i.name = sle.item_code
            WHERE sle.qty_after_transaction != 0
            ORDER BY sle.item_code
        """
        
        stock_entries = frappe.db.sql(query, {
            'company': doc.company,
            'warehouse': doc.warehouse,
            'report_date': doc.report_date
        }, as_dict=1)
        
        if not stock_entries:
            return {
                'status': 'warning',
                'message': 'No stock found for the selected warehouse and date'
            }
        
        # Clear existing entries
        doc.set("stock_balance_entry", [])
        
        # Add new entries
        for entry in stock_entries:
            # Apply criterion filter
            if doc.criterion == "Reorder Level":
                # Only include items below reorder level
                if flt(entry.get('qty', 0)) >= flt(entry.get('reorder_level', 0)):
                    continue
            
            doc.append('stock_balance_entry', {
                'item_code': entry.get('item_code'),
                'item_name': entry.get('item_name'),
                'item_group': entry.get('item_group'),
                'uom': entry.get('stock_uom'),
                'warehouse': entry.get('warehouse'),
                'qty': entry.get('qty', 0),
                'cost_price': entry.get('cost_price', 0),
                'reorder_level': entry.get('reorder_level', 0),
                'safety_stock': entry.get('safety_stock', 0),
                'minimum_order_qty': entry.get('minimum_order_qty', 0),
                'report_date': entry.get('posting_date'),
                'ref': doc.name
            })
        
        doc.save(ignore_permissions=True)
        
        return {
            'status': 'success',
            'message': f'Successfully fetched {len(doc.stock_balance_entry)} items',
            'count': len(doc.stock_balance_entry)
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Stock Balance Fetch Error")
        return {
            'status': 'error',
            'message': str(e)
        }


@frappe.whitelist()
def fetch_stock_balance_simple(docname):
    """
    Simpler version using frappe.get_all - more compatible but slightly slower
    """
    try:
        doc = frappe.get_doc('Stock Availability', docname)
        
        if not doc.company or not doc.warehouse or not doc.report_date:
            return {
                'status': 'error',
                'message': 'Company, Warehouse, and Report Date are required'
            }
        
        # Fetch all stock ledger entries
        filters = {
            'company': doc.company,
            'warehouse': doc.warehouse,
            'docstatus': 1,
            'posting_date': ['<=', doc.report_date]
        }
        
        fields = [
            'item_code', 'warehouse', 'stock_uom', 'posting_date',
            'qty_after_transaction', 'valuation_rate', 'outgoing_rate', 
            'incoming_rate', 'creation'
        ]
        
        # Try to add custom fields if they exist
        sle_meta = frappe.get_meta('Stock Ledger Entry')
        optional_fields = [
            'custom_reorder_level',
            'custom_safety_stock', 'custom_minimum_order_qty',
            'custom_reorder_qty'
        ]
        
        for field in optional_fields:
            if any(f.fieldname == field for f in sle_meta.fields):
                fields.append(field)
        
        stock_entries = frappe.get_all(
            'Stock Ledger Entry',
            filters=filters,
            fields=fields,
            order_by='item_code, warehouse, creation desc',
            limit_page_length=5000
        )
        
        if not stock_entries:
            return {
                'status': 'warning',
                'message': 'No stock found for the selected warehouse and date'
            }
        
        # Get latest entry per item
        latest_entries = {}
        for entry in stock_entries:
            key = (entry.get('item_code'), entry.get('warehouse'))
            if key not in latest_entries:
                latest_entries[key] = entry
        
        # Clear existing entries
        doc.set("stock_balance_entry", [])
        
        # Add new entries
        for entry in latest_entries.values():
            # Skip zero quantity
            if not entry.get('qty_after_transaction'):
                continue
            
            # Get item details
            item_code = entry.get('item_code')
            try:
                item = frappe.get_cached_doc('Item', item_code)
            except frappe.DoesNotExistError:
                continue
            
            # Determine reorder level
            reorder_level = 0
            for field in ['custom_reorder_level', 'reorder_level']:
                if entry.get(field):
                    reorder_level = entry.get(field)
                    break
            
            # Determine safety stock
            safety_stock = 0
            for field in ['custom_safety_stock', 'safety_stock']:
                if entry.get(field):
                    safety_stock = entry.get(field)
                    break
            
            # Determine minimum order qty
            min_order_qty = 0
            for field in ['custom_minimum_order_qty', 'minimum_order_qty', 'min_order_qty']:
                if entry.get(field):
                    min_order_qty = entry.get(field)
                    break
            
            # Skip if doesn't meet criterion
            if doc.criterion == "Reorder Level":
                if flt(entry.get('qty_after_transaction', 0)) >= flt(reorder_level):
                    continue
            
            doc.append('stock_balance_entry', {
                'item_code': entry.get('item_code'),
                'item_name': item.get('item_name'),
                'item_group': item.get('item_group'),
                'uom': entry.get('stock_uom'),
                'warehouse': entry.get('warehouse'),
                'qty': entry.get('qty_after_transaction', 0),
                'cost_price': entry.get('valuation_rate') or entry.get('outgoing_rate') or entry.get('incoming_rate') or 0,
                'reorder_level': reorder_level,
                'safety_stock': safety_stock,
                'minimum_order_qty': min_order_qty,
                'report_date': entry.get('posting_date'),
                'ref': doc.name
            })
        
        doc.save(ignore_permissions=True)
        
        return {
            'status': 'success',
            'message': f'Successfully fetched {len(doc.stock_balance_entry)} items',
            'count': len(doc.stock_balance_entry)
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Stock Balance Fetch Error")
        return {
            'status': 'error',
            'message': str(e)
        }


@frappe.whitelist()
def send_stock_availability_report(docname):
    """
    Send stock availability report via email
    """
    try:
        doc = frappe.get_doc("Stock Availability", docname)
        
        # Validate email recipients
        email_recipients = [e.strip() for e in (doc.send_to or "").split(",") if e.strip()]
        if not email_recipients:
            frappe.throw('No email recipients specified')
        
        cc_recipients = [e.strip() for e in (doc.cc or "").split(",") if e.strip()]
        bcc_recipients = [e.strip() for e in (doc.bcc or "").split(",") if e.strip()]
        
        # Get currency
        currency = frappe.db.get_value('Company', doc.company, 'default_currency') or "NGN"
        
        # Build email content
        subject = f"Stock Availability Report - {doc.warehouse} ({doc.report_date})"
        
        if doc.criterion == "Availability":
            message = build_availability_email(doc, currency)
        else:
            message = build_reorder_email(doc, currency)
        
        # Send email
        frappe.sendmail(
            recipients=email_recipients,
            cc=cc_recipients,
            bcc=bcc_recipients,
            subject=subject,
            message=message,
            delayed=False
        )
        
        # Update document
        doc.add_comment('Comment', f'Stock report emailed to {", ".join(email_recipients)}')
        
        return {
            'status': 'success',
            'message': f'Report sent to {len(email_recipients)} recipient(s)'
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Stock Availability Email Error")
        return {
            'status': 'error',
            'message': str(e)
        }


def build_availability_email(doc, currency):
    """Build email for availability report"""
    table_rows = []
    total_amount = 0
    
    for idx, entry in enumerate(doc.get("stock_balance_entry", []), 1):
        amount = flt(entry.qty) * flt(entry.cost_price)
        total_amount += amount
        
        row_color = "#ffffff" if idx % 2 == 0 else "#f9f9f9"
        
        table_rows.append(f"""
            <tr style="background: {row_color};">
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{idx}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{entry.item_code}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{entry.item_name or ''}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: center;">{entry.uom}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right;">{flt(entry.qty, 2)}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right;">{flt(entry.reorder_level, 2)}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right;">{fmt_money(entry.cost_price, currency=currency)}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right; font-weight: 600;">{fmt_money(amount, currency=currency)}</td>
            </tr>
        """)
    
    return f"""
    <div style="max-width: 1200px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0; font-size: 24px;">Stock Availability Report</h2>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Comprehensive Stock Analysis</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
                <div>
                    <p style="margin: 5px 0; color: #666;"><strong>Warehouse:</strong> {doc.warehouse}</p>
                    <p style="margin: 5px 0; color: #666;"><strong>Report Date:</strong> {frappe.format(doc.report_date, {'fieldtype': 'Date'})}</p>
                </div>
                <div>
                    <p style="margin: 5px 0; color: #666;"><strong>Company:</strong> {doc.company}</p>
                    <p style="margin: 5px 0; color: #666;"><strong>Total Items:</strong> {len(doc.stock_balance_entry)}</p>
                </div>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">#</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">Item Code</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">Item Name</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: center;">UOM</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Qty</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Reorder Lvl</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Cost Price</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
                <tfoot>
                    <tr style="background: #f5f5f5; font-weight: bold;">
                        <td colspan="7" style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Total Stock Value:</td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0; text-align: right; color: #10b981; font-size: 16px;">{fmt_money(total_amount, currency=currency)}</td>
                    </tr>
                </tfoot>
            </table>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{get_url_to_form('Stock Availability', doc.name)}" 
                   style="display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; font-weight: 500;">
                    View Full Report
                </a>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666; font-size: 12px;">
                <p>This is an automated report from {doc.company}</p>
                <p>Generated on {frappe.format(now_datetime(), {'fieldtype': 'Datetime'})}</p>
            </div>
        </div>
    </div>
    """


def build_reorder_email(doc, currency):
    """Build email for reorder level report"""
    table_rows = []
    total_reorder_amount = 0
    
    for idx, entry in enumerate(doc.get("stock_balance_entry", []), 1):
        reorder_qty = max(0, flt(entry.reorder_level) - flt(entry.qty))
        reorder_amount = reorder_qty * flt(entry.cost_price)
        total_reorder_amount += reorder_amount
        
        row_color = "#fff5f5" if reorder_qty > 0 else "#ffffff"
        status_color = "#ef4444" if reorder_qty > 0 else "#10b981"
        status_text = "Below Reorder" if reorder_qty > 0 else "Adequate"
        
        table_rows.append(f"""
            <tr style="background: {row_color};">
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{idx}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{entry.item_code}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{entry.item_name or ''}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: center;">{entry.uom}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right;">{flt(entry.qty, 2)}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right;">{flt(entry.reorder_level, 2)}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right; font-weight: 600; color: {status_color};">{flt(reorder_qty, 2)}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right;">{fmt_money(entry.cost_price, currency=currency)}</td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; text-align: right; font-weight: 600;">{fmt_money(reorder_amount, currency=currency)}</td>
            </tr>
        """)
    
    return f"""
    <div style="max-width: 1200px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="background: linear-gradient(135deg, #f59e0b 0%, #dc2626 100%); padding: 30px; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0; font-size: 24px;">⚠️ Stock Reorder Alert</h2>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Items Below Reorder Level</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                <p style="margin: 0; color: #92400e;"><strong>Action Required:</strong> The following items are below their reorder levels and require procurement.</p>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
                <div>
                    <p style="margin: 5px 0; color: #666;"><strong>Warehouse:</strong> {doc.warehouse}</p>
                    <p style="margin: 5px 0; color: #666;"><strong>Report Date:</strong> {frappe.format(doc.report_date, {'fieldtype': 'Date'})}</p>
                </div>
                <div>
                    <p style="margin: 5px 0; color: #666;"><strong>Company:</strong> {doc.company}</p>
                    <p style="margin: 5px 0; color: #666;"><strong>Items to Reorder:</strong> {len(doc.stock_balance_entry)}</p>
                </div>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">#</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">Item Code</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">Item Name</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: center;">UOM</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Current Qty</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Reorder Lvl</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Reorder Qty</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Cost Price</th>
                        <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Reorder Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
                <tfoot>
                    <tr style="background: #fef3c7; font-weight: bold;">
                        <td colspan="8" style="padding: 12px; border: 1px solid #e0e0e0; text-align: right;">Total Reorder Cost:</td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0; text-align: right; color: #dc2626; font-size: 16px;">{fmt_money(total_reorder_amount, currency=currency)}</td>
                    </tr>
                </tfoot>
            </table>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{get_url_to_form('Stock Availability', doc.name)}" 
                   style="display: inline-block; padding: 12px 30px; background: #dc2626; color: white; text-decoration: none; border-radius: 5px; font-weight: 500;">
                    View Full Report & Create Purchase Request
                </a>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666; font-size: 12px;">
                <p>This is an automated reorder alert from {doc.company}</p>
                <p>Generated on {frappe.format(now_datetime(), {'fieldtype': 'Datetime'})}</p>
            </div>
        </div>
    </div>
    """


@frappe.whitelist()
def create_material_request(docname):
    """
    Create Material Request from Stock Availability
    """
    try:
        doc = frappe.get_doc("Stock Availability", docname)
        
        if not doc.get("stock_balance_entry"):
            return {
                'status': 'error',
                'message': 'No items in stock balance to create Material Request'
            }
        
        # Create Material Request
        mr = frappe.new_doc("Material Request")
        mr.material_request_type = "Purchase"
        mr.company = doc.company
        mr.schedule_date = add_days(today(), 7)  # Default 7 days from now
        
        # Add custom field reference if it exists
        if frappe.db.exists("Custom Field", {"dt": "Material Request", "fieldname": "custom_stock_availability"}):
            mr.custom_stock_availability = doc.name
        
        items_added = 0
        for entry in doc.get("stock_balance_entry", []):
            reorder_qty = max(0, flt(entry.reorder_level) - flt(entry.qty))
            
            # Use minimum order qty if specified
            if entry.minimum_order_qty and reorder_qty > 0:
                reorder_qty = max(reorder_qty, entry.minimum_order_qty)
            
            if reorder_qty > 0:
                mr.append("items", {
                    "item_code": entry.item_code,
                    "qty": reorder_qty,
                    "warehouse": doc.warehouse,
                    "schedule_date": mr.schedule_date,
                    "uom": entry.uom,
                    "rate": entry.cost_price
                })
                items_added += 1
        
        if items_added == 0:
            return {
                'status': 'warning',
                'message': 'No items require reordering'
            }
        
        mr.insert()
        
        return {
            'status': 'success',
            'message': f'Material Request {mr.name} created with {items_added} items',
            'docname': mr.name
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Material Request Creation Error")
        return {
            'status': 'error',
            'message': str(e)
        }


@frappe.whitelist()
def export_to_excel(docname):
    """
    Export Stock Availability to Excel
    Returns downloadable file
    """
    try:
        from frappe.utils.xlsxutils import make_xlsx
        
        doc = frappe.get_doc("Stock Availability", docname)
        currency = frappe.db.get_value('Company', doc.company, 'default_currency') or "NGN"
        
        # Prepare data
        data = []
        
        # Header
        data.append([
            "Stock Availability Report",
            "",
            "",
            "",
            "",
            "",
            "",
            ""
        ])
        data.append([
            f"Warehouse: {doc.warehouse}",
            f"Report Date: {doc.report_date}",
            f"Company: {doc.company}",
            "",
            "",
            "",
            "",
            ""
        ])
        data.append([])  # Empty row
        
        # Column headers
        if doc.criterion == "Availability":
            data.append([
                "S/N",
                "Item Code",
                "Item Name",
                "Item Group",
                "UOM",
                "Quantity",
                "Reorder Level",
                "Safety Stock",
                "Min Order Qty",
                f"Cost Price ({currency})",
                f"Amount ({currency})"
            ])
        else:
            data.append([
                "S/N",
                "Item Code",
                "Item Name",
                "Item Group",
                "UOM",
                "Current Qty",
                "Reorder Level",
                "Safety Stock",
                "Reorder Qty",
                "Min Order Qty",
                f"Cost Price ({currency})",
                f"Reorder Amount ({currency})"
            ])
        
        # Data rows
        total_amount = 0
        for idx, entry in enumerate(doc.get("stock_balance_entry", []), 1):
            if doc.criterion == "Availability":
                amount = flt(entry.qty) * flt(entry.cost_price)
                total_amount += amount
                data.append([
                    idx,
                    entry.item_code,
                    entry.item_name or "",
                    entry.item_group or "",
                    entry.uom,
                    flt(entry.qty, 2),
                    flt(entry.reorder_level, 2),
                    flt(entry.safety_stock, 2),
                    flt(entry.minimum_order_qty, 2),
                    flt(entry.cost_price, 2),
                    flt(amount, 2)
                ])
            else:
                reorder_qty = max(0, flt(entry.reorder_level) - flt(entry.qty))
                reorder_amount = reorder_qty * flt(entry.cost_price)
                total_amount += reorder_amount
                data.append([
                    idx,
                    entry.item_code,
                    entry.item_name or "",
                    entry.item_group or "",
                    entry.uom,
                    flt(entry.qty, 2),
                    flt(entry.reorder_level, 2),
                    flt(entry.safety_stock, 2),
                    flt(reorder_qty, 2),
                    flt(entry.minimum_order_qty, 2),
                    flt(entry.cost_price, 2),
                    flt(reorder_amount, 2)
                ])
        
        # Total row
        if doc.criterion == "Availability":
            data.append([
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Total:",
                flt(total_amount, 2)
            ])
        else:
            data.append([
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Total:",
                flt(total_amount, 2)
            ])
        
        # Footer
        data.append([])
        data.append([
            f"Generated on: {now_datetime().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            ""
        ])
        
        # Create Excel file
        xlsx_file = make_xlsx(data, "Stock Availability Report")
        
        frappe.response['filename'] = f'stock_availability_{doc.name}.xlsx'
        frappe.response['filecontent'] = xlsx_file.getvalue()
        frappe.response['type'] = 'binary'
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Excel Export Error")
        frappe.throw(f"Error exporting to Excel: {str(e)}")