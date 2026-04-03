# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, add_days, add_months


class FixedAssetMaintenance(Document):
    def validate(self):
        """Validate maintenance document"""
        self.validate_asset()
        self.validate_dates()
        self.calculate_total_cost()
        self.validate_scheduling()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.maintenance_date:
            frappe.throw(_("Maintenance Date is required"))
        
        if not self.maintenance_type:
            frappe.throw(_("Maintenance Type is required"))
        
        if not self.maintenance_description:
            frappe.throw(_("Maintenance Description is required"))
    
    def on_submit(self):
        """On submit operations"""
        self.update_asset_maintenance_status()
        self.create_maintenance_journal_entry()
        
        if self.is_scheduled:
            self.schedule_next_maintenance()
        
        self.update_warranty_if_extended()
    
    def on_cancel(self):
        """On cancel operations"""
        self.revert_asset_maintenance_status()
        self.cancel_journal_entry()
    
    def on_update_after_submit(self):
        """After submit updates"""
        if self.status == "Completed":
            self.on_maintenance_completion()
    
    def validate_asset(self):
        """Validate asset details"""
        if not self.asset:
            frappe.throw(_("Asset is required"))
        
        if not frappe.db.exists("Fixed Asset", self.asset):
            frappe.throw(_("Invalid Asset"))
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if asset.docstatus != 1:
            frappe.throw(_("Asset must be submitted before maintenance"))
        
        if hasattr(asset, 'asset_status') and asset.asset_status == "Disposed":
            frappe.throw(_("Cannot perform maintenance on disposed asset"))
        
        # Fetch asset details
        self.asset_name = asset.asset_name
    
    def validate_dates(self):
        """Validate dates"""
        if self.maintenance_date and getdate(self.maintenance_date) > getdate(nowdate()):
            frappe.throw(_("Maintenance Date cannot be in the future"))
        
        if self.completion_date:
            if getdate(self.completion_date) < getdate(self.maintenance_date):
                frappe.throw(_("Completion Date cannot be before Maintenance Date"))
            
            if getdate(self.completion_date) > getdate(nowdate()):
                frappe.throw(_("Completion Date cannot be in the future"))
        
        if self.scheduled_date and self.maintenance_date:
            if getdate(self.maintenance_date) < getdate(self.scheduled_date):
                frappe.msgprint(_("Maintenance performed earlier than scheduled"), indicator="orange")
    
    def calculate_total_cost(self):
        """Calculate total maintenance cost"""
        self.total_cost = (
            flt(self.maintenance_cost) + 
            flt(self.parts_cost) + 
            flt(self.labor_cost)
        )
    
    def validate_scheduling(self):
        """Validate scheduling parameters"""
        if self.is_scheduled:
            if not self.frequency:
                frappe.throw(_("Frequency is required for recurring maintenance"))
            
            if not self.next_maintenance_date:
                self.calculate_next_maintenance_date()
    
    def calculate_next_maintenance_date(self):
        """Calculate next maintenance date based on frequency"""
        if not self.is_scheduled or not self.frequency:
            return
        
        base_date = self.completion_date or self.maintenance_date or nowdate()
        
        frequency_map = {
            "Weekly": 7,
            "Bi-Weekly": 14,
            "Monthly": 30,
            "Quarterly": 90,
            "Half-Yearly": 180,
            "Annual": 365,
            "Bi-Annual": 730
        }
        
        days = frequency_map.get(self.frequency, 30)
        self.next_maintenance_date = add_days(base_date, days)
    
    def update_asset_maintenance_status(self):
        """Update asset maintenance status"""
        if self.status == "In Progress":
            asset = frappe.get_doc("Fixed Asset", self.asset)
            
            if hasattr(asset, 'is_under_maintenance'):
                asset.db_set("is_under_maintenance", 1)
            
            if hasattr(asset, 'asset_status'):
                asset.db_set("asset_status", "Under Maintenance")
    
    def revert_asset_maintenance_status(self):
        """Revert asset maintenance status"""
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if hasattr(asset, 'is_under_maintenance'):
            asset.db_set("is_under_maintenance", 0)
        
        # Recalculate status
        if hasattr(asset, 'asset_status'):
            if hasattr(asset, 'disposal_date') and asset.disposal_date:
                asset.db_set("asset_status", "Disposed")
            elif hasattr(asset, 'available_for_use_date') and (not asset.available_for_use_date or getdate(asset.available_for_use_date) > getdate(nowdate())):
                asset.db_set("asset_status", "Not Yet Available")
            elif flt(asset.current_gross_value) <= flt(asset.residual_value):
                asset.db_set("asset_status", "Fully Depreciated")
            else:
                asset.db_set("asset_status", "Active")
    
    def on_maintenance_completion(self):
        """Handle maintenance completion"""
        if not self.completion_date:
            self.completion_date = nowdate()
            self.db_set("completion_date", self.completion_date)
        
        # Remove under maintenance flag
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if hasattr(asset, 'is_under_maintenance'):
            asset.db_set("is_under_maintenance", 0)
        
        # Recalculate asset status
        if hasattr(asset, 'asset_status'):
            if hasattr(asset, 'disposal_date') and asset.disposal_date:
                asset.db_set("asset_status", "Disposed")
            elif flt(asset.current_gross_value) <= flt(asset.residual_value):
                asset.db_set("asset_status", "Fully Depreciated")
            else:
                asset.db_set("asset_status", "Active")
        
        # Schedule next maintenance if recurring
        if self.is_scheduled:
            self.schedule_next_maintenance()
    
    def schedule_next_maintenance(self):
        """Schedule next maintenance if recurring"""
        if not self.is_scheduled or not self.frequency:
            return
        
        if not self.next_maintenance_date:
            self.calculate_next_maintenance_date()
            self.db_set("next_maintenance_date", self.next_maintenance_date)
        
        # Create next maintenance record only if current is completed
        if self.status == "Completed" and self.docstatus == 1:
            try:
                next_maintenance = frappe.copy_doc(self)
                next_maintenance.maintenance_date = self.next_maintenance_date
                next_maintenance.scheduled_date = self.next_maintenance_date
                next_maintenance.status = "Scheduled"
                next_maintenance.completion_date = None
                next_maintenance.completed_by = None
                next_maintenance.work_performed = None
                next_maintenance.parts_replaced = None
                next_maintenance.maintenance_cost = 0
                next_maintenance.parts_cost = 0
                next_maintenance.labor_cost = 0
                next_maintenance.total_cost = 0
                next_maintenance.journal_entry = None
                next_maintenance.post_maintenance_condition = None
                next_maintenance.downtime_hours = 0
                next_maintenance.before_maintenance_image = None
                next_maintenance.after_maintenance_image = None
                next_maintenance.maintenance_invoice = None
                
                next_maintenance.flags.ignore_permissions = True
                next_maintenance.insert()
                
                frappe.msgprint(_("Next maintenance scheduled for {0}: {1}").format(
                    self.next_maintenance_date,
                    frappe.utils.get_link_to_form("Fixed Asset Maintenance", next_maintenance.name)
                ))
            
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title="Next Maintenance Scheduling Failed"
                )
    
    def update_warranty_if_extended(self):
        """Update asset warranty if extended"""
        if self.warranty_extended and self.new_warranty_expiry:
            asset = frappe.get_doc("Fixed Asset", self.asset)
            if hasattr(asset, 'warranty_expiry_date'):
                asset.db_set("warranty_expiry_date", self.new_warranty_expiry)
                frappe.msgprint(_("Asset warranty extended to {0}").format(self.new_warranty_expiry))
    
    def create_maintenance_journal_entry(self):
        """Create journal entry for maintenance cost"""
        if not self.create_journal_entry or self.journal_entry:
            return
        
        if flt(self.total_cost) <= 0:
            frappe.msgprint(_("No cost to record"), indicator="orange")
            return
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if not self.expense_account:
            frappe.throw(_("Expense Account is required to create journal entry"))
        
        # Get default cash account
        default_cash_account = frappe.db.get_value("Company", self.company, "default_cash_account")
        
        if not default_cash_account:
            frappe.throw(_("Default Cash Account not set for Company {0}").format(self.company))
        
        # Create Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = self.maintenance_date
        je.company = self.company
        je.user_remark = f"Maintenance Cost - {self.asset_name} ({self.maintenance_type})"
        
        # Debit: Maintenance Expense Account
        je.append("accounts", {
            "account": self.expense_account,
            "debit_in_account_currency": flt(self.total_cost),
            "reference_type": "Fixed Asset Maintenance",
            "reference_name": self.name,
            "cost_center": self.cost_center or asset.cost_center
        })
        
        # Credit: Cash/Bank Account
        je.append("accounts", {
            "account": default_cash_account,
            "credit_in_account_currency": flt(self.total_cost),
            "reference_type": "Fixed Asset Maintenance",
            "reference_name": self.name,
            "cost_center": self.cost_center or asset.cost_center
        })
        
        try:
            je.flags.ignore_permissions = True
            je.insert()
            je.submit()
            
            self.db_set("journal_entry", je.name)
            
            frappe.msgprint(_("Journal Entry {0} created successfully").format(
                frappe.utils.get_link_to_form("Journal Entry", je.name)))
        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title="Maintenance Journal Entry Creation Failed"
            )
            frappe.throw(_("Failed to create journal entry: {0}").format(str(e)))
    
    def cancel_journal_entry(self):
        """Cancel associated journal entry"""
        if self.journal_entry:
            try:
                je = frappe.get_doc("Journal Entry", self.journal_entry)
                if je.docstatus == 1:
                    je.flags.ignore_permissions = True
                    je.cancel()
                self.db_set("journal_entry", None)
                frappe.msgprint(_("Journal Entry {0} cancelled").format(je.name))
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Journal Entry Cancellation Failed: {self.journal_entry}"
                )


# Whitelisted methods

@frappe.whitelist()
def get_asset_maintenance_history(asset):
    """Get maintenance history for an asset"""
    if not asset:
        return []
    
    history = frappe.get_all("Fixed Asset Maintenance",
        filters={
            "asset": asset,
            "docstatus": 1
        },
        fields=[
            "name", "maintenance_date", "maintenance_type", "status",
            "total_cost", "work_performed", "post_maintenance_condition",
            "completion_date", "downtime_hours"
        ],
        order_by="maintenance_date desc"
    )
    
    return history


@frappe.whitelist()
def get_maintenance_due_assets(company=None, maintenance_type=None, days=7):
    """Get assets due for maintenance"""
    filters = {
        "docstatus": 1,
        "is_scheduled": 1,
        "status": "Scheduled",
        "next_maintenance_date": ["<=", add_days(nowdate(), cint(days))]
    }
    
    if company:
        filters["company"] = company
    
    if maintenance_type:
        filters["maintenance_type"] = maintenance_type
    
    due_maintenance = frappe.get_all("Fixed Asset Maintenance",
        filters=filters,
        fields=[
            "name", "asset", "asset_name", "maintenance_type",
            "next_maintenance_date", "maintenance_description", "frequency"
        ],
        order_by="next_maintenance_date"
    )
    
    return due_maintenance


@frappe.whitelist()
def mark_maintenance_completed(maintenance_name, completion_details):
    """Mark maintenance as completed"""
    import json
    if isinstance(completion_details, str):
        completion_details = json.loads(completion_details)
    
    maintenance = frappe.get_doc("Fixed Asset Maintenance", maintenance_name)
    
    if maintenance.status == "Completed":
        frappe.throw(_("Maintenance is already completed"))
    
    # Update completion details
    maintenance.status = "Completed"
    maintenance.completion_date = completion_details.get("completion_date") or nowdate()
    maintenance.completed_by = completion_details.get("completed_by") or frappe.session.user
    maintenance.work_performed = completion_details.get("work_performed")
    maintenance.parts_replaced = completion_details.get("parts_replaced")
    maintenance.post_maintenance_condition = completion_details.get("post_maintenance_condition")
    maintenance.downtime_hours = completion_details.get("downtime_hours")
    
    maintenance.flags.ignore_permissions = True
    maintenance.save()
    
    return maintenance.name


@frappe.whitelist()
def create_maintenance_reminder():
    """Send maintenance reminder notifications (scheduled task)"""
    # Get maintenance due in next 7 days
    due_maintenance = frappe.get_all("Fixed Asset Maintenance",
        filters={
            "docstatus": 1,
            "is_scheduled": 1,
            "status": "Scheduled",
            "next_maintenance_date": ["between", [nowdate(), add_days(nowdate(), 7)]]
        },
        fields=["name", "asset", "asset_name", "maintenance_type", "next_maintenance_date", "company"]
    )
    
    if not due_maintenance:
        return
    
    # Group by company
    company_maintenance = {}
    for maint in due_maintenance:
        if maint.company not in company_maintenance:
            company_maintenance[maint.company] = []
        company_maintenance[maint.company].append(maint)
    
    # Send notifications
    for company, maintenances in company_maintenance.items():
        # Get maintenance managers/users with appropriate role
        recipients = frappe.get_all("User",
            filters={
                "enabled": 1,
                "name": ["in", frappe.get_all("Has Role", 
                    filters={"role": ["in", ["System Manager", "Accounts Manager"]]},
                    pluck="parent"
                )]
            },
            pluck="email"
        )
        
        if not recipients:
            continue
        
        message = f"""
        <h3>Upcoming Asset Maintenance - {company}</h3>
        <p>The following assets are due for maintenance in the next 7 days:</p>
        <br>
        <table border="1" cellpadding="5" style="border-collapse: collapse;">
            <tr style="background-color: #f0f0f0;">
                <th>Asset</th>
                <th>Maintenance Type</th>
                <th>Due Date</th>
                <th>Action</th>
            </tr>
        """
        
        for maint in maintenances:
            link = frappe.utils.get_url_to_form("Fixed Asset Maintenance", maint.name)
            message += f"""
            <tr>
                <td>{maint.asset_name}</td>
                <td>{maint.maintenance_type}</td>
                <td>{frappe.utils.formatdate(maint.next_maintenance_date)}</td>
                <td><a href="{link}">View</a></td>
            </tr>
            """
        
        message += "</table>"
        
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=f"Asset Maintenance Due - {company}",
                message=message
            )
        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title="Maintenance Reminder Email Failed"
            )


@frappe.whitelist()
def get_maintenance_cost_summary(asset=None, company=None, from_date=None, to_date=None):
    """Get maintenance cost summary"""
    filters = {"docstatus": 1}
    
    if asset:
        filters["asset"] = asset
    
    if company:
        filters["company"] = company
    
    if from_date:
        filters["maintenance_date"] = [">=", from_date]
    
    if to_date:
        if "maintenance_date" in filters:
            filters["maintenance_date"] = ["between", [from_date, to_date]]
        else:
            filters["maintenance_date"] = ["<=", to_date]
    
    maintenance_records = frappe.get_all("Fixed Asset Maintenance",
        filters=filters,
        fields=["maintenance_type", "total_cost", "maintenance_date"]
    )
    
    # Summarize by type
    summary = {}
    for record in maintenance_records:
        mtype = record.maintenance_type
        if mtype not in summary:
            summary[mtype] = {"count": 0, "total_cost": 0}
        
        summary[mtype]["count"] += 1
        summary[mtype]["total_cost"] += flt(record.total_cost)
    
    return summary