# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
# Copyright (c) 2026, Kunle Oduntan and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, now, get_url


class FixedAssetTransfer(Document):
    def validate(self):
        """Validate transfer"""
        self.validate_transfer_details()
        self.validate_assets()
        self.validate_same_source_destination()
        self.calculate_totals()
        self.set_status()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.transfer_items:
            frappe.throw(_("Please add at least one asset to transfer"))
        
        # Check all assets are valid
        for item in self.transfer_items:
            asset = frappe.get_doc("Fixed Asset", item.asset)
            if asset.docstatus != 1:
                frappe.throw(_("Row {0}: Asset {1} must be submitted").format(item.idx, item.asset))
    
    def on_submit(self):
        """On submit operations"""
        self.update_assets_on_transfer()
        self.create_transfer_history()
        self.status = "Approved"
        self.db_set("status", "Approved")
        
        # Send approval notification
        self.send_transfer_submitted_email()
    
    def on_cancel(self):
        """On cancel operations"""
        self.reverse_asset_updates()
        self.status = "Cancelled"
        self.db_set("status", "Cancelled")
        
        # Send cancellation notification
        self.send_transfer_cancelled_email()
    
    def validate_transfer_details(self):
        """Validate transfer details"""
        if not self.transfer_items:
            frappe.throw(_("Please add at least one asset to transfer"))
        
        # Validate based on transfer type
        if self.transfer_type == "Complete Transfer":
            if not self.to_location:
                frappe.throw(_("To Location is required for Complete Transfer"))
            if not self.to_department:
                frappe.throw(_("To Department is required for Complete Transfer"))
            if not self.to_cost_center:
                frappe.throw(_("To Cost Center is required for Complete Transfer"))
        
        elif self.transfer_type == "Location Change":
            if not self.to_location:
                frappe.throw(_("To Location is required for Location Change"))
        
        elif self.transfer_type == "Department Change":
            if not self.to_department:
                frappe.throw(_("To Department is required for Department Change"))
        
        elif self.transfer_type == "Custodian Change":
            if not self.to_custodian:
                frappe.throw(_("To Custodian is required for Custodian Change"))
        
        elif self.transfer_type == "Cost Center Change":
            if not self.to_cost_center:
                frappe.throw(_("To Cost Center is required for Cost Center Change"))
    
    def validate_same_source_destination(self):
        """Validate that source and destination are different"""
        if self.transfer_type == "Location Change":
            if self.from_location == self.to_location:
                frappe.throw(_("From Location and To Location cannot be the same"))
        
        if self.transfer_type == "Department Change":
            if self.from_department == self.to_department:
                frappe.throw(_("From Department and To Department cannot be the same"))
        
        if self.transfer_type == "Custodian Change":
            if self.from_custodian == self.to_custodian:
                frappe.throw(_("From Custodian and To Custodian cannot be the same"))
        
        if self.transfer_type == "Cost Center Change":
            if self.from_cost_center == self.to_cost_center:
                frappe.throw(_("From Cost Center and To Cost Center cannot be the same"))
    
    def validate_assets(self):
        """Validate assets in transfer"""
        seen_assets = set()
        
        for item in self.transfer_items:
            # Check duplicate
            if item.asset in seen_assets:
                frappe.throw(_("Row {0}: Asset {1} is duplicated").format(item.idx, item.asset))
            seen_assets.add(item.asset)
            
            if not frappe.db.exists("Fixed Asset", item.asset):
                frappe.throw(_("Row {0}: Asset {1} does not exist").format(item.idx, item.asset))
            
            asset = frappe.get_doc("Fixed Asset", item.asset)
            
            if asset.docstatus != 1:
                frappe.throw(_("Row {0}: Asset must be submitted").format(item.idx))
            
            if hasattr(asset, 'asset_status') and asset.asset_status in ["Disposed", "Sold", "Scrapped"]:
                frappe.throw(_("Row {0}: Cannot transfer {1} asset").format(item.idx, asset.asset_status))
            
            # Auto-populate from fields from first asset
            if item.idx == 1:
                if not self.from_location and hasattr(asset, 'current_location'):
                    self.from_location = asset.current_location
                
                if not self.from_department and hasattr(asset, 'department'):
                    self.from_department = asset.department
                
                if not self.from_cost_center and hasattr(asset, 'cost_center'):
                    self.from_cost_center = asset.cost_center
                
                if not self.from_custodian and hasattr(asset, 'custodian'):
                    self.from_custodian = asset.custodian
    
    def calculate_totals(self):
        """Calculate totals"""
        self.total_assets = len(self.transfer_items)
        
        total_value = 0
        for item in self.transfer_items:
            total_value += flt(item.current_book_value)
        
        self.total_book_value = total_value
    
    def set_status(self):
        """Set transfer status based on workflow"""
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 2:
            self.status = "Cancelled"
        elif self.received_by and self.receipt_date:
            self.status = "Received"
        elif self.delivered_by and self.delivery_date:
            self.status = "Delivered"
        elif self.docstatus == 1:
            self.status = "Approved"
    
    def update_assets_on_transfer(self):
        """Update asset details using db_set() - respects submittable Fixed Asset"""
        for item in self.transfer_items:
            # Update based on transfer type using db_set()
            if self.transfer_type in ["Location Change", "Complete Transfer"] and self.to_location:
                frappe.db.set_value("Fixed Asset", item.asset, "current_location", self.to_location)
            
            if self.transfer_type in ["Department Change", "Complete Transfer"] and self.to_department:
                frappe.db.set_value("Fixed Asset", item.asset, "department", self.to_department)
            
            if self.transfer_type in ["Custodian Change", "Complete Transfer"] and self.to_custodian:
                frappe.db.set_value("Fixed Asset", item.asset, "custodian", self.to_custodian)
            
            if self.transfer_type in ["Cost Center Change", "Complete Transfer"] and self.to_cost_center:
                frappe.db.set_value("Fixed Asset", item.asset, "cost_center", self.to_cost_center)
            
            # Update last transfer date
            frappe.db.set_value("Fixed Asset", item.asset, "last_transfer_date", self.transfer_date)
        
        frappe.msgprint(_("{0} asset(s) updated successfully").format(len(self.transfer_items)), indicator="green")
    
    def reverse_asset_updates(self):
        """Reverse asset updates on cancellation using db_set()"""
        for item in self.transfer_items:
            # Revert to from details using db_set()
            if self.transfer_type in ["Location Change", "Complete Transfer"] and self.from_location:
                frappe.db.set_value("Fixed Asset", item.asset, "current_location", self.from_location)
            
            if self.transfer_type in ["Department Change", "Complete Transfer"] and self.from_department:
                frappe.db.set_value("Fixed Asset", item.asset, "department", self.from_department)
            
            if self.transfer_type in ["Custodian Change", "Complete Transfer"] and self.from_custodian:
                frappe.db.set_value("Fixed Asset", item.asset, "custodian", self.from_custodian)
            
            if self.transfer_type in ["Cost Center Change", "Complete Transfer"] and self.from_cost_center:
                frappe.db.set_value("Fixed Asset", item.asset, "cost_center", self.from_cost_center)
        
        frappe.msgprint(_("Asset updates reversed"), indicator="orange")
    
    def create_transfer_history(self):
        """Create audit trail for transfer"""
        for item in self.transfer_items:
            # Create a comment/note on the asset
            comment_text = f"""
            <b>Asset Transfer</b><br>
            Transfer Type: {self.transfer_type}<br>
            From: {self.from_location or ''} / {self.from_department or ''}<br>
            To: {self.to_location or ''} / {self.to_department or ''}<br>
            Transfer Date: {frappe.utils.formatdate(self.transfer_date)}<br>
            Reference: {self.name}
            """
            
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Fixed Asset",
                "reference_name": item.asset,
                "content": comment_text
            }).insert(ignore_permissions=True)
    
    # Email notification methods
    
    def send_transfer_submitted_email(self):
        """Send email when transfer is submitted/approved"""
        recipients = self.get_notification_recipients()
        
        if not recipients:
            return
        
        subject = f"Asset Transfer Approved - {self.name}"
        
        message = self.get_transfer_email_template(
            title="Asset Transfer Approved",
            status="Approved",
            icon="✅",
            color="#00a82d"
        )
        
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=subject,
                message=message,
                reference_doctype=self.doctype,
                reference_name=self.name
            )
        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Transfer Email Failed: {self.name}"
            )
    
    def send_transfer_cancelled_email(self):
        """Send email when transfer is cancelled"""
        recipients = self.get_notification_recipients()
        
        if not recipients:
            return
        
        subject = f"Asset Transfer Cancelled - {self.name}"
        
        message = self.get_transfer_email_template(
            title="Asset Transfer Cancelled",
            status="Cancelled",
            icon="❌",
            color="#d63939"
        )
        
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=subject,
                message=message,
                reference_doctype=self.doctype,
                reference_name=self.name
            )
        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Transfer Cancellation Email Failed: {self.name}"
            )
    
    def get_notification_recipients(self):
        """Get list of email recipients for notifications"""
        recipients = []
        
        # Add creator
        creator_email = frappe.db.get_value("User", self.owner, "email")
        if creator_email:
            recipients.append(creator_email)
        
        # Add from custodian
        if self.from_custodian:
            from_email = frappe.db.get_value("User", self.from_custodian, "email")
            if from_email and from_email not in recipients:
                recipients.append(from_email)
        
        # Add to custodian
        if self.to_custodian:
            to_email = frappe.db.get_value("User", self.to_custodian, "email")
            if to_email and to_email not in recipients:
                recipients.append(to_email)
        
        # Add approver
        if self.approved_by:
            approver_email = frappe.db.get_value("User", self.approved_by, "email")
            if approver_email and approver_email not in recipients:
                recipients.append(approver_email)
        
        # Add users with specific roles
        role_users = frappe.get_all("Has Role",
            filters={"role": ["in", ["Accounts Manager", "System Manager"]]},
            fields=["parent"],
            distinct=True
        )
        
        for user in role_users:
            user_email = frappe.db.get_value("User", user.parent, "email")
            if user_email and user_email not in recipients:
                recipients.append(user_email)
        
        return recipients
    
    def get_transfer_email_template(self, title, status, icon, color):
        """Get beautiful HTML email template"""
        
        # Build assets table
        assets_html = ""
        for item in self.transfer_items:
            assets_html += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;">{item.asset_code or ''}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{item.asset_name or ''}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{item.current_location or ''}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{frappe.utils.fmt_money(item.current_book_value)}</td>
            </tr>
            """
        
        transfer_url = get_url(f"/app/fixed-asset-transfer/{self.name}")
        
        message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .email-container {{ max-width: 800px; margin: 0 auto; }}
                .header {{ background-color: {color}; color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                .content {{ padding: 30px; background-color: #ffffff; }}
                .info-section {{ background-color: #f9f9f9; padding: 20px; margin: 20px 0; border-left: 4px solid {color}; }}
                .info-row {{ display: flex; margin: 10px 0; }}
                .info-label {{ font-weight: bold; width: 200px; color: #555; }}
                .info-value {{ flex: 1; }}
                .assets-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .assets-table th {{ background-color: {color}; color: white; padding: 12px; text-align: left; }}
                .assets-table td {{ padding: 10px; border: 1px solid #ddd; }}
                .assets-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary-box {{ background-color: #e7f3ff; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .action-button {{ display: inline-block; padding: 12px 30px; background-color: {color}; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background-color: #f0f0f0; padding: 20px; text-align: center; font-size: 12px; color: #666; }}
                .status-badge {{ display: inline-block; padding: 5px 15px; background-color: {color}; color: white; border-radius: 20px; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>{icon} {title}</h1>
                    <p>{self.name}</p>
                </div>
                
                <div class="content">
                    <p>Dear Team,</p>
                    
                    <p>This email confirms that an asset transfer has been <strong>{status.lower()}</strong>.</p>
                    
                    <div class="info-section">
                        <h3 style="margin-top: 0;">Transfer Details</h3>
                        
                        <div class="info-row">
                            <div class="info-label">Transfer Number:</div>
                            <div class="info-value"><strong>{self.name}</strong></div>
                        </div>
                        
                        <div class="info-row">
                            <div class="info-label">Transfer Date:</div>
                            <div class="info-value">{frappe.utils.formatdate(self.transfer_date)}</div>
                        </div>
                        
                        <div class="info-row">
                            <div class="info-label">Transfer Type:</div>
                            <div class="info-value">{self.transfer_type}</div>
                        </div>
                        
                        <div class="info-row">
                            <div class="info-label">Status:</div>
                            <div class="info-value"><span class="status-badge">{status}</span></div>
                        </div>
                        
                        <div class="info-row">
                            <div class="info-label">Company:</div>
                            <div class="info-value">{self.company}</div>
                        </div>
                    </div>
                    
                    <div class="info-section">
                        <h3 style="margin-top: 0;">Transfer Route</h3>
                        
                        <table style="width: 100%;">
                            <tr>
                                <td style="width: 45%; vertical-align: top;">
                                    <h4 style="color: #d63939; margin: 0 0 10px 0;">📤 FROM</h4>
                                    <div><strong>Location:</strong> {self.from_location or 'N/A'}</div>
                                    <div><strong>Department:</strong> {self.from_department or 'N/A'}</div>
                                    <div><strong>Custodian:</strong> {self.from_custodian or 'N/A'}</div>
                                    <div><strong>Cost Center:</strong> {self.from_cost_center or 'N/A'}</div>
                                </td>
                                <td style="width: 10%; text-align: center; vertical-align: middle; font-size: 30px;">
                                    ➡️
                                </td>
                                <td style="width: 45%; vertical-align: top;">
                                    <h4 style="color: #00a82d; margin: 0 0 10px 0;">📥 TO</h4>
                                    <div><strong>Location:</strong> {self.to_location or 'N/A'}</div>
                                    <div><strong>Department:</strong> {self.to_department or 'N/A'}</div>
                                    <div><strong>Custodian:</strong> {self.to_custodian or 'N/A'}</div>
                                    <div><strong>Cost Center:</strong> {self.to_cost_center or 'N/A'}</div>
                                </td>
                            </tr>
                        </table>
                    </div>
                    
                    <h3>Assets Being Transferred</h3>
                    <table class="assets-table">
                        <thead>
                            <tr>
                                <th>Asset Code</th>
                                <th>Asset Name</th>
                                <th>Current Location</th>
                                <th>Book Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {assets_html}
                        </tbody>
                    </table>
                    
                    <div class="summary-box">
                        <strong>📊 Summary:</strong><br>
                        Total Assets: <strong>{self.total_assets}</strong><br>
                        Total Book Value: <strong>{frappe.utils.fmt_money(self.total_book_value)}</strong>
                    </div>
                    
                    {f'<div class="info-section"><strong>Remarks:</strong><br>{self.remarks}</div>' if self.remarks else ''}
                    
                    <div style="text-align: center;">
                        <a href="{transfer_url}" class="action-button">View Transfer Document</a>
                    </div>
                    
                    <div style="margin-top: 30px; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
                        <strong>⚠️ Action Required:</strong><br>
                        {"Please ensure assets are properly handed over and received." if status == "Approved" else "This transfer has been cancelled. No action required."}
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated email from the Asset Management System.</p>
                    <p>© {frappe.utils.nowdate().year} {self.company}. All rights reserved.</p>
                    <p style="margin-top: 10px;">
                        <a href="{transfer_url}" style="color: #666;">View in System</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return message


# Whitelisted methods

@frappe.whitelist()
def approve_transfer(transfer_name):
    """Approve transfer"""
    transfer = frappe.get_doc("Fixed Asset Transfer", transfer_name)
    
    if transfer.docstatus != 1:
        frappe.throw(_("Transfer must be submitted first"))
    
    transfer.db_set("approved_by", frappe.session.user)
    transfer.db_set("approval_date", now())
    transfer.db_set("status", "Approved")
    
    # Send approval email
    send_status_update_email(transfer, "Approved", "✅", "#00a82d")
    
    return {"success": True, "message": _("Transfer approved successfully")}


@frappe.whitelist()
def mark_in_transit(transfer_name):
    """Mark transfer as in transit"""
    transfer = frappe.get_doc("Fixed Asset Transfer", transfer_name)
    
    if transfer.status != "Approved":
        frappe.throw(_("Transfer must be approved first"))
    
    transfer.db_set("status", "In Transit")
    
    # Send in-transit email
    send_status_update_email(transfer, "In Transit", "🚚", "#fd7e14")
    
    return {"success": True, "message": _("Transfer marked as in transit")}


@frappe.whitelist()
def mark_delivered(transfer_name, delivered_by=None):
    """Mark transfer as delivered"""
    transfer = frappe.get_doc("Fixed Asset Transfer", transfer_name)
    
    if transfer.status not in ["Approved", "In Transit"]:
        frappe.throw(_("Invalid status for delivery"))
    
    transfer.db_set("delivered_by", delivered_by or frappe.session.user)
    transfer.db_set("delivery_date", now())
    transfer.db_set("status", "Delivered")
    
    # Send delivery email
    send_delivery_email(transfer)
    
    return {"success": True, "message": _("Transfer marked as delivered")}


@frappe.whitelist()
def mark_received(transfer_name, received_by=None, receipt_remarks=None):
    """Mark transfer as received"""
    transfer = frappe.get_doc("Fixed Asset Transfer", transfer_name)
    
    if transfer.status != "Delivered":
        frappe.throw(_("Transfer must be delivered first"))
    
    transfer.db_set("received_by", received_by or frappe.session.user)
    transfer.db_set("receipt_date", now())
    transfer.db_set("status", "Received")
    
    if receipt_remarks:
        transfer.db_set("remarks", (transfer.remarks or "") + "\n\nReceipt Remarks: " + receipt_remarks)
    
    # Send receipt confirmation email
    send_receipt_email(transfer)
    
    return {"success": True, "message": _("Transfer marked as received")}


def send_status_update_email(transfer, status, icon, color):
    """Send status update email"""
    recipients = transfer.get_notification_recipients()
    
    if not recipients:
        return
    
    subject = f"Transfer Status Update - {transfer.name} ({status})"
    
    message = transfer.get_transfer_email_template(
        title=f"Transfer Status: {status}",
        status=status,
        icon=icon,
        color=color
    )
    
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            reference_doctype=transfer.doctype,
            reference_name=transfer.name
        )
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"Transfer Status Email Failed: {transfer.name}"
        )


def send_delivery_email(transfer):
    """Send delivery notification email"""
    recipients = []
    
    # Notify receiver
    if transfer.to_custodian:
        to_email = frappe.db.get_value("User", transfer.to_custodian, "email")
        if to_email:
            recipients.append(to_email)
    
    # Notify creator
    creator_email = frappe.db.get_value("User", transfer.owner, "email")
    if creator_email and creator_email not in recipients:
        recipients.append(creator_email)
    
    if not recipients:
        return
    
    subject = f"Assets Delivered - Please Confirm Receipt - {transfer.name}"
    
    transfer_url = get_url(f"/app/fixed-asset-transfer/{transfer.name}")
    
    message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #0dcaf0; color: white; padding: 30px; text-align: center; }}
            .content {{ padding: 30px; }}
            .alert-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; margin: 20px 0; }}
            .button {{ display: inline-block; padding: 15px 30px; background-color: #00a82d; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📦 Assets Delivered</h1>
            <p>{transfer.name}</p>
        </div>
        <div class="content">
            <p>Dear {transfer.to_custodian or 'Team'},</p>
            
            <div class="alert-box">
                <strong>🚚 Action Required:</strong><br>
                Assets have been delivered and are awaiting your confirmation of receipt.
            </div>
            
            <p><strong>Delivery Details:</strong></p>
            <ul>
                <li>Delivered By: {transfer.delivered_by}</li>
                <li>Delivery Date: {frappe.utils.format_datetime(transfer.delivery_date)}</li>
                <li>Number of Assets: {transfer.total_assets}</li>
                <li>Location: {transfer.to_location or 'N/A'}</li>
            </ul>
            
            <p><strong>Next Steps:</strong></p>
            <ol>
                <li>Physically inspect and verify all assets</li>
                <li>Check asset condition</li>
                <li>Confirm receipt in the system</li>
                <li>Report any discrepancies immediately</li>
            </ol>
            
            <div style="text-align: center;">
                <a href="{transfer_url}" class="button">View Transfer & Confirm Receipt</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            reference_doctype=transfer.doctype,
            reference_name=transfer.name
        )
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"Delivery Email Failed: {transfer.name}"
        )


def send_receipt_email(transfer):
    """Send receipt confirmation email"""
    recipients = transfer.get_notification_recipients()
    
    if not recipients:
        return
    
    subject = f"Transfer Completed - Assets Received - {transfer.name}"
    
    message = transfer.get_transfer_email_template(
        title="Transfer Completed Successfully",
        status="Received",
        icon="✅",
        color="#00a82d"
    )
    
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            reference_doctype=transfer.doctype,
            reference_name=transfer.name
        )
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"Receipt Email Failed: {transfer.name}"
        )


@frappe.whitelist()
def get_asset_transfer_details(asset):
    """Get asset details for transfer"""
    if not asset:
        return {}
    
    if not frappe.db.exists("Fixed Asset", asset):
        frappe.throw(_("Asset not found"))
    
    asset_doc = frappe.get_doc("Fixed Asset", asset)
    
    return {
        "asset_code": asset_doc.asset_code,
        "asset_name": asset_doc.asset_name,
        "current_location": asset_doc.current_location if hasattr(asset_doc, 'current_location') else None,
        "current_custodian": asset_doc.custodian if hasattr(asset_doc, 'custodian') else None,
        "current_book_value": asset_doc.current_gross_value if hasattr(asset_doc, 'current_gross_value') else asset_doc.gross_purchase_amount,
        "department": asset_doc.department if hasattr(asset_doc, 'department') else None,
        "cost_center": asset_doc.cost_center if hasattr(asset_doc, 'cost_center') else None
    }


@frappe.whitelist()
def get_transfer_summary(company=None, from_date=None, to_date=None):
    """Get transfer summary statistics"""
    filters = {"docstatus": 1}
    
    if company:
        filters["company"] = company
    
    if from_date:
        filters["transfer_date"] = [">=", from_date]
    
    if to_date:
        if "transfer_date" in filters:
            filters["transfer_date"] = ["between", [from_date, to_date]]
        else:
            filters["transfer_date"] = ["<=", to_date]
    
    # Get total transfers
    total_transfers = frappe.db.count("Fixed Asset Transfer", filters)
    
    # Get by status
    by_status = {}
    for status in ["Approved", "In Transit", "Delivered", "Received"]:
        by_status[status] = frappe.db.count("Fixed Asset Transfer", {
            **filters,
            "status": status
        })
    
    return {
        "total_transfers": total_transfers,
        "by_status": by_status
    }


@frappe.whitelist()
def get_asset_transfer_history(asset):
    """Get transfer history for an asset"""
    if not asset:
        return []
    
    transfers = frappe.get_all("Fixed Asset Transfer Item",
        filters={"asset": asset, "docstatus": 1},
        fields=["parent"],
        distinct=True
    )
    
    history = []
    for transfer in transfers:
        transfer_doc = frappe.get_doc("Fixed Asset Transfer", transfer.parent)
        history.append({
            "name": transfer_doc.name,
            "transfer_date": transfer_doc.transfer_date,
            "transfer_type": transfer_doc.transfer_type,
            "from_location": transfer_doc.from_location,
            "to_location": transfer_doc.to_location,
            "from_department": transfer_doc.from_department,
            "to_department": transfer_doc.to_department,
            "status": transfer_doc.status
        })
    
    return sorted(history, key=lambda x: x["transfer_date"], reverse=True)


@frappe.whitelist()
def scan_asset_qr(qr_code):
    """Scan asset QR code and return asset details"""
    if not qr_code:
        return {"success": False, "message": _("No QR code provided")}
    
    # QR code format is typically: ASSET-{asset_code} or just the asset name
    asset_name = None
    
    # Try to find asset by QR code field
    asset_name = frappe.db.get_value("Fixed Asset", {"qr_code": qr_code}, "name")
    
    # If not found, try by asset_code
    if not asset_name:
        asset_name = frappe.db.get_value("Fixed Asset", {"asset_code": qr_code}, "name")
    
    # If still not found, try direct name match
    if not asset_name:
        if frappe.db.exists("Fixed Asset", qr_code):
            asset_name = qr_code
    
    if not asset_name:
        return {
            "success": False,
            "message": _("Asset not found for QR code: {0}").format(qr_code)
        }
    
    # Get asset details
    asset_details = get_asset_transfer_details(asset_name)
    
    if asset_details:
        return {
            "success": True,
            "asset": asset_name,
            "details": asset_details,
            "message": _("Asset found: {0}").format(asset_details.get("asset_name"))
        }
    else:
        return {
            "success": False,
            "message": _("Could not fetch asset details")
        }
        
@frappe.whitelist()
def export_transfer_data(transfer_name):
    """Export transfer data for Excel/CSV"""
    if not frappe.db.exists("Fixed Asset Transfer", transfer_name):
        frappe.throw(_("Transfer not found"))
    
    transfer = frappe.get_doc("Fixed Asset Transfer", transfer_name)
    
    data = []
    for item in transfer.transfer_items:
        data.append({
            "asset_code": item.asset_code or "",
            "asset_name": item.asset_name or "",
            "current_location": item.current_location or "",
            "current_custodian": item.current_custodian or "",
            "current_book_value": item.current_book_value or 0,
            "condition_at_transfer": item.condition_at_transfer if hasattr(item, 'condition_at_transfer') else "Good"
        })
    
    return data