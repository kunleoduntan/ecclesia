# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, nowdate


class FixedAssetVerification(Document):
    def validate(self):
        """Validate verification document"""
        self.calculate_summary()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.verification_details:
            frappe.throw(_("Please add assets to verify"))
    
    def on_submit(self):
        """On submit operations"""
        self.update_asset_locations()
        self.create_discrepancy_report()
    
    def on_cancel(self):
        """On cancel operations"""
        self.status = "Cancelled"
    
    def calculate_summary(self):
        """Calculate verification summary"""
        if not self.verification_details:
            return
        
        self.total_assets_to_verify = len(self.verification_details)
        
        verified_count = 0
        missing_count = 0
        discrepancy_count = 0
        
        for item in self.verification_details:
            if item.verified:
                verified_count += 1
            
            if item.physical_condition == "Missing":
                missing_count += 1
            
            if item.discrepancy:
                discrepancy_count += 1
        
        self.assets_verified = verified_count
        self.assets_missing = missing_count
        self.assets_with_discrepancies = discrepancy_count
        
        # Calculate completion percentage
        if self.total_assets_to_verify > 0:
            self.verification_completion_percentage = (verified_count / self.total_assets_to_verify) * 100
    
    def update_asset_locations(self):
        """Update asset locations based on verification"""
        for item in self.verification_details:
            if item.verified and item.actual_location:
                asset = frappe.get_doc("Fixed Asset", item.asset)
                
                # Only update if location changed
                if asset.current_location != item.actual_location:
                    asset.db_set("current_location", item.actual_location)
                    
                    # Create asset transfer record
                    self.create_location_transfer(asset, item)
    
    def create_location_transfer(self, asset, verification_item):
        """Create asset transfer record for location change"""
        try:
            transfer = frappe.get_doc({
                "doctype": "Fixed Asset Transfer",
                "company": self.company,
                "transfer_date": self.verification_date,
                "transfer_type": "Location Change",
                "from_location": verification_item.expected_location,
                "to_location": verification_item.actual_location,
                "status": "Received",
                "remarks": f"Location updated during verification {self.name}"
            })
            
            transfer.append("transfer_items", {
                "asset": asset.name,
                "asset_code": asset.asset_code,
                "asset_name": asset.asset_name,
                "current_location": verification_item.expected_location,
                "current_book_value": asset.current_value,
                "condition_at_transfer": verification_item.physical_condition
            })
            
            transfer.insert(ignore_permissions=True)
            transfer.submit()
        
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Asset Transfer Creation Failed")
    
    def create_discrepancy_report(self):
        """Create discrepancy report if needed"""
        discrepancies = [d for d in self.verification_details if d.discrepancy]
        
        if not discrepancies:
            return
        
        # Send notification to follow-up person
        if self.follow_up_assigned_to:
            self.send_discrepancy_notification(discrepancies)
    
    def send_discrepancy_notification(self, discrepancies):
        """Send email notification for discrepancies"""
        message = f"""
        <h3>Asset Verification Discrepancies Found</h3>
        <p>Verification Period: {self.verification_period}</p>
        <p>Verification Date: {self.verification_date}</p>
        <p>Total Discrepancies: {len(discrepancies)}</p>
        <br>
        <table border="1" cellpadding="5">
            <tr>
                <th>Asset Code</th>
                <th>Asset Name</th>
                <th>Discrepancy Type</th>
                <th>Remarks</th>
            </tr>
        """
        
        for disc in discrepancies:
            message += f"""
            <tr>
                <td>{disc.asset_code}</td>
                <td>{disc.asset_name}</td>
                <td>{disc.discrepancy_type}</td>
                <td>{disc.remarks or ""}</td>
            </tr>
            """
        
        message += "</table>"
        
        frappe.sendmail(
            recipients=[self.follow_up_assigned_to],
            subject=f"Asset Verification Discrepancies - {self.verification_period}",
            message=message
        )


@frappe.whitelist()
def get_assets_for_verification(company, asset_category=None, location=None, department=None, cost_center=None):
    """Get assets for verification based on filters"""
    
    filters = {
        "company": company,
        "docstatus": 1,
        "status": ["not in", ["Disposed", "Cancelled"]]
    }
    
    if asset_category:
        # Handle multi-select
        categories = asset_category.split(",")
        filters["asset_category"] = ["in", categories]
    
    if location:
        filters["current_location"] = location
    
    if department:
        filters["department"] = department
    
    if cost_center:
        filters["cost_center"] = cost_center
    
    assets = frappe.get_all("Fixed Asset",
        filters=filters,
        fields=[
            "name", "asset_code", "asset_name", "asset_category",
            "current_location", "custodian", "current_value"
        ]
    )
    
    verification_items = []
    
    for asset in assets:
        verification_items.append({
            "asset": asset.name,
            "asset_code": asset.asset_code,
            "asset_name": asset.asset_name,
            "expected_location": asset.current_location,
            "physical_condition": "Good",
            "verified": 0,
            "discrepancy": 0
        })
    
    return verification_items


@frappe.whitelist()
def process_qr_scan(qr_data, verification_doc):
    """Process QR code scan during verification"""
    import json
    
    try:
        data = json.loads(qr_data)
        asset_code = data.get("asset_code")
        
        if not asset_code:
            return {"success": False, "message": _("Invalid QR Code")}
        
        # Get asset
        asset = frappe.get_all("Fixed Asset",
            filters={"asset_code": asset_code},
            fields=["name", "asset_name", "current_location", "status"]
        )
        
        if not asset:
            return {"success": False, "message": _("Asset not found")}
        
        asset = asset[0]
        
        # Update verification record
        verification = frappe.get_doc("Fixed Asset Verification", verification_doc)
        
        # Find the asset in verification details
        for item in verification.verification_details:
            if item.asset == asset.name:
                item.qr_code_scanned = 1
                item.scan_timestamp = nowdate()
                item.verified = 1
                break
        
        verification.save()
        
        return {
            "success": True,
            "asset": asset,
            "message": _("Asset {0} scanned successfully").format(asset_code)
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "QR Scan Error")
        return {"success": False, "message": str(e)}