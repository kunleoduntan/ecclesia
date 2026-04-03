# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, add_months, add_days, date_diff


class FixedAssetInsurance(Document):
    def validate(self):
        """Validate insurance document"""
        self.validate_asset()
        self.validate_dates()
        self.validate_coverage()
        self.calculate_coverage_percentage()
        self.calculate_payment_schedule()
        self.update_policy_status()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.policy_number:
            frappe.throw(_("Policy Number is required"))
        
        if not self.sum_insured:
            frappe.throw(_("Sum Insured is required"))
        
        if not self.premium_amount:
            frappe.throw(_("Premium Amount is required"))
        
        if not self.insurance_provider:
            frappe.throw(_("Insurance Provider is required"))
    
    def on_submit(self):
        """On submit operations"""
        self.update_asset_insurance_status()
        self.create_premium_journal_entry()
        self.policy_status = "Active"
        self.db_set("policy_status", "Active")
    
    def on_cancel(self):
        """On cancel operations"""
        self.revert_asset_insurance_status()
        self.cancel_journal_entry()
        self.policy_status = "Cancelled"
        self.db_set("policy_status", "Cancelled")
    
    def on_update_after_submit(self):
        """After submit updates"""
        self.check_policy_expiry()
        self.update_payment_totals()
    
    def validate_asset(self):
        """Validate asset details"""
        if not self.asset:
            frappe.throw(_("Asset is required"))
        
        if not frappe.db.exists("Fixed Asset", self.asset):
            frappe.throw(_("Invalid Asset"))
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if asset.docstatus != 1:
            frappe.throw(_("Asset must be submitted before insurance"))
        
        if hasattr(asset, 'asset_status') and asset.asset_status == "Disposed":
            frappe.throw(_("Cannot insure a disposed asset"))
        
        # Fetch asset details
        self.asset_name = asset.asset_name
        self.asset_code = asset.asset_code
        self.asset_category = asset.asset_category
        self.asset_value = asset.current_gross_value or asset.gross_purchase_amount
        
        if hasattr(asset, 'current_location'):
            self.asset_location = asset.current_location
    
    def validate_dates(self):
        """Validate dates"""
        if not self.policy_start_date or not self.policy_end_date:
            frappe.throw(_("Policy Start Date and End Date are required"))
        
        if getdate(self.policy_end_date) <= getdate(self.policy_start_date):
            frappe.throw(_("Policy End Date must be after Policy Start Date"))
        
        # Calculate policy term in months
        months = date_diff(self.policy_end_date, self.policy_start_date) / 30
        self.policy_term_months = int(months)
        
        # Calculate renewal date (30 days before expiry)
        self.renewal_date = add_days(self.policy_end_date, -30)
    
    def validate_coverage(self):
        """Validate coverage details"""
        if flt(self.sum_insured) <= 0:
            frappe.throw(_("Sum Insured must be greater than zero"))
        
        if flt(self.premium_amount) <= 0:
            frappe.throw(_("Premium Amount must be greater than zero"))
        
        # Check if sum insured is reasonable
        if self.asset_value:
            if flt(self.sum_insured) > flt(self.asset_value) * 1.5:
                frappe.msgprint(
                    _("Warning: Sum Insured ({0}) is significantly higher than asset value ({1})").format(
                        self.sum_insured, self.asset_value
                    ),
                    indicator="orange"
                )
            elif flt(self.sum_insured) < flt(self.asset_value) * 0.7:
                frappe.msgprint(
                    _("Warning: Sum Insured ({0}) is less than 70% of asset value ({1}). Asset may be under-insured").format(
                        self.sum_insured, self.asset_value
                    ),
                    indicator="orange"
                )
    
    def calculate_coverage_percentage(self):
        """Calculate coverage percentage"""
        if self.sum_insured and self.asset_value:
            self.coverage_percentage = (flt(self.sum_insured) / flt(self.asset_value)) * 100
    
    def calculate_payment_schedule(self):
        """Calculate payment schedule based on premium frequency"""
        if not self.premium_frequency or not self.premium_amount:
            return
        
        frequency_months = {
            "Annual": 12,
            "Semi-Annual": 6,
            "Quarterly": 3,
            "Monthly": 1
        }
        
        months = frequency_months.get(self.premium_frequency, 12)
        
        # Calculate number of installments
        if self.policy_term_months:
            self.number_of_installments = max(1, int(self.policy_term_months / months))
            
            # Calculate installment amount
            if self.number_of_installments > 1:
                self.installment_amount = flt(self.premium_amount) / self.number_of_installments
            else:
                self.installment_amount = self.premium_amount
        
        # Calculate next payment date
        if not self.next_payment_date and self.policy_start_date:
            self.next_payment_date = self.policy_start_date
    
    def update_policy_status(self):
        """Update policy status based on dates"""
        if self.docstatus == 0:
            self.policy_status = "Draft"
            return
        
        if self.docstatus == 2:
            self.policy_status = "Cancelled"
            return
        
        today = getdate(nowdate())
        
        if not self.policy_end_date:
            return
        
        if getdate(self.policy_end_date) < today:
            self.policy_status = "Expired"
        elif getdate(self.renewal_date) <= today < getdate(self.policy_end_date):
            self.policy_status = "Expiring Soon"
            self.days_to_expiry = date_diff(self.policy_end_date, today)
        elif getdate(self.policy_start_date) <= today <= getdate(self.policy_end_date):
            self.policy_status = "Active"
            self.days_to_expiry = date_diff(self.policy_end_date, today)
        else:
            self.policy_status = "Not Started"
    
    def update_asset_insurance_status(self):
        """Update asset with insurance information"""
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if hasattr(asset, 'is_insured'):
            asset.db_set("is_insured", 1)
        
        if hasattr(asset, 'insurance_policy_number'):
            asset.db_set("insurance_policy_number", self.policy_number)
        
        if hasattr(asset, 'insurance_expiry_date'):
            asset.db_set("insurance_expiry_date", self.policy_end_date)
        
        if hasattr(asset, 'insurance_value'):
            asset.db_set("insurance_value", self.sum_insured)
    
    def revert_asset_insurance_status(self):
        """Revert asset insurance status"""
        # Check if there are other active policies
        other_policies = frappe.db.count("Fixed Asset Insurance", {
            "asset": self.asset,
            "docstatus": 1,
            "policy_status": ["in", ["Active", "Expiring Soon"]],
            "name": ["!=", self.name]
        })
        
        if other_policies == 0:
            asset = frappe.get_doc("Fixed Asset", self.asset)
            
            if hasattr(asset, 'is_insured'):
                asset.db_set("is_insured", 0)
            
            if hasattr(asset, 'insurance_policy_number'):
                asset.db_set("insurance_policy_number", None)
            
            if hasattr(asset, 'insurance_expiry_date'):
                asset.db_set("insurance_expiry_date", None)
            
            if hasattr(asset, 'insurance_value'):
                asset.db_set("insurance_value", 0)
    
    def check_policy_expiry(self):
        """Check and update policy status based on dates"""
        self.update_policy_status()
        
        if self.policy_status != self.get_value_before_save("policy_status"):
            self.db_set("policy_status", self.policy_status)
            
            if self.policy_status == "Expiring Soon":
                frappe.msgprint(
                    _("Policy is expiring in {0} days. Consider renewal.").format(self.days_to_expiry),
                    indicator="orange"
                )
    
    def update_payment_totals(self):
        """Update total paid and claims from history"""
        if self.insurance_claims:
            total_claimed = sum(flt(claim.claim_amount) for claim in self.insurance_claims)
            total_settled = sum(flt(claim.approved_amount) for claim in self.insurance_claims if claim.claim_status == "Settled")
            
            self.db_set("total_claims_amount", total_claimed)
            self.db_set("total_settled_amount", total_settled)
    
    def create_premium_journal_entry(self):
        """Create journal entry for premium payment"""
        if not self.create_journal_entry_for_premium or self.journal_entry:
            return
        
        if flt(self.premium_amount) <= 0:
            frappe.msgprint(_("No premium amount to record"), indicator="orange")
            return
        
        if not self.insurance_expense_account:
            frappe.throw(_("Insurance Expense Account is required to create journal entry"))
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        # Get default cash account
        default_cash_account = frappe.db.get_value("Company", self.company, "default_cash_account")
        
        if not default_cash_account:
            frappe.throw(_("Default Cash Account not set for Company {0}").format(self.company))
        
        # Create Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = self.policy_start_date
        je.company = self.company
        je.user_remark = f"Insurance Premium - {self.asset_name} (Policy: {self.policy_number})"
        
        # For annual payment, use prepaid insurance if account is set
        if self.premium_frequency == "Annual" and self.prepaid_insurance_account:
            # Debit: Prepaid Insurance (Asset)
            je.append("accounts", {
                "account": self.prepaid_insurance_account,
                "debit_in_account_currency": flt(self.premium_amount),
                "reference_type": "Fixed Asset Insurance",
                "reference_name": self.name,
                "cost_center": self.cost_center or (asset.cost_center if hasattr(asset, 'cost_center') else None)
            })
        else:
            # Debit: Insurance Expense
            je.append("accounts", {
                "account": self.insurance_expense_account,
                "debit_in_account_currency": flt(self.premium_amount),
                "reference_type": "Fixed Asset Insurance",
                "reference_name": self.name,
                "cost_center": self.cost_center or (asset.cost_center if hasattr(asset, 'cost_center') else None)
            })
        
        # Credit: Cash/Bank
        je.append("accounts", {
            "account": default_cash_account,
            "credit_in_account_currency": flt(self.premium_amount),
            "reference_type": "Fixed Asset Insurance",
            "reference_name": self.name,
            "cost_center": self.cost_center or (asset.cost_center if hasattr(asset, 'cost_center') else None)
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
                title="Insurance Journal Entry Creation Failed"
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
def get_asset_details(asset):
    """Get asset details for insurance form"""
    if not asset:
        return {}
    
    asset_doc = frappe.get_doc("Fixed Asset", asset)
    
    return {
        "asset_code": asset_doc.asset_code,
        "asset_name": asset_doc.asset_name,
        "asset_category": asset_doc.asset_category,
        "location": asset_doc.current_location if hasattr(asset_doc, 'current_location') else None,
        "current_value": asset_doc.current_gross_value or asset_doc.gross_purchase_amount,
        "cost_center": asset_doc.cost_center if hasattr(asset_doc, 'cost_center') else None
    }


@frappe.whitelist()
def get_insurance_renewal_due(company=None, days=30):
    """Get insurance policies due for renewal"""
    filters = {
        "docstatus": 1,
        "policy_status": ["in", ["Active", "Expiring Soon"]],
        "renewal_date": ["<=", add_days(nowdate(), cint(days))]
    }
    
    if company:
        filters["company"] = company
    
    due_policies = frappe.get_all("Fixed Asset Insurance",
        filters=filters,
        fields=[
            "name", "asset", "asset_name", "policy_number",
            "insurance_provider", "policy_end_date", "renewal_date",
            "premium_amount", "sum_insured", "company"
        ],
        order_by="renewal_date"
    )
    
    return due_policies


@frappe.whitelist()
def update_policy_status(doc_name):
    """Update policy status based on current date"""
    doc = frappe.get_doc("Fixed Asset Insurance", doc_name)
    doc.update_policy_status()
    doc.save()
    
    return doc.policy_status


@frappe.whitelist()
def renew_policy(source_name):
    """Create a new policy based on existing policy"""
    from frappe.model.mapper import get_mapped_doc
    
    def set_missing_values(source, target):
        target.policy_status = "Draft"
        target.docstatus = 0
        
        # Set new policy dates
        target.policy_start_date = source.policy_end_date
        target.policy_end_date = add_months(source.policy_end_date, source.policy_term_months or 12)
        
        # Clear old references
        target.journal_entry = None
        target.insurance_claims = []
        target.next_payment_date = target.policy_start_date
    
    target_doc = get_mapped_doc("Fixed Asset Insurance", source_name, {
        "Fixed Asset Insurance": {
            "doctype": "Fixed Asset Insurance",
            "field_no_map": [
                "journal_entry",
                "insurance_claims",
                "total_claims_amount",
                "total_settled_amount"
            ]
        }
    }, None, set_missing_values)
    
    return target_doc


@frappe.whitelist()
def cancel_policy(doc_name, reason, refund_amount=0):
    """Cancel insurance policy"""
    import json
    if isinstance(reason, str):
        try:
            data = json.loads(reason)
            reason = data.get("reason", reason)
            refund_amount = data.get("refund_amount", 0)
        except:
            pass
    
    doc = frappe.get_doc("Fixed Asset Insurance", doc_name)
    
    if doc.policy_status == "Cancelled":
        frappe.throw(_("Policy is already cancelled"))
    
    doc.policy_status = "Cancelled"
    doc.cancellation_reason = reason
    doc.refund_amount = flt(refund_amount)
    
    doc.add_comment("Comment", f"Policy cancelled. Reason: {reason}. Refund: {refund_amount}")
    
    doc.flags.ignore_permissions = True
    doc.save()
    
    # Update asset
    doc.revert_asset_insurance_status()
    
    return True


@frappe.whitelist()
def create_payment_reminder(doc_name):
    """Create payment reminder for next premium"""
    doc = frappe.get_doc("Fixed Asset Insurance", doc_name)
    
    if not doc.next_payment_date:
        frappe.throw(_("No payment date scheduled"))
    
    # This would integrate with your reminder system
    # For now, just return the reminder details
    return {
        "reminder_date": doc.next_payment_date,
        "amount": doc.installment_amount or doc.premium_amount,
        "policy_number": doc.policy_number
    }


@frappe.whitelist()
def send_insurance_renewal_reminders():
    """Send insurance renewal reminders (scheduled task)"""
    due_policies = get_insurance_renewal_due(days=30)
    
    if not due_policies:
        return
    
    # Group by company
    company_policies = {}
    for policy in due_policies:
        if policy.company not in company_policies:
            company_policies[policy.company] = []
        company_policies[policy.company].append(policy)
    
    # Send notifications
    for company, policies in company_policies.items():
        # Get users with appropriate role
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
        
        # Create beautiful HTML email
        message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #2e86de; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .policy-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .policy-table th {{ background-color: #f0f0f0; padding: 12px; text-align: left; border: 1px solid #ddd; }}
                .policy-table td {{ padding: 10px; border: 1px solid #ddd; }}
                .policy-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .alert {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
                .urgent {{ color: #dc3545; font-weight: bold; }}
                .warning {{ color: #fd7e14; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🛡️ Insurance Renewal Reminder</h2>
                <p>{company}</p>
            </div>
            
            <div class="content">
                <div class="alert">
                    <strong>⚠️ Action Required:</strong> The following insurance policies are due for renewal in the next 30 days.
                </div>
                
                <p>Dear Team,</p>
                <p>This is an automated reminder that <strong>{len(policies)}</strong> insurance {"policy" if len(policies) == 1 else "policies"} require your attention for renewal.</p>
                
                <table class="policy-table">
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Policy Number</th>
                            <th>Provider</th>
                            <th>Sum Insured</th>
                            <th>Premium</th>
                            <th>Expiry Date</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for policy in policies:
            days_left = date_diff(policy.policy_end_date, nowdate())
            status_class = "urgent" if days_left <= 7 else "warning" if days_left <= 15 else ""
            status_text = f"{days_left} days left"
            
            policy_link = frappe.utils.get_url_to_form("Fixed Asset Insurance", policy.name)
            
            message += f"""
                        <tr>
                            <td><a href="{policy_link}">{policy.asset_name}</a></td>
                            <td>{policy.policy_number}</td>
                            <td>{policy.insurance_provider}</td>
                            <td>{frappe.utils.fmt_money(policy.sum_insured)}</td>
                            <td>{frappe.utils.fmt_money(policy.premium_amount)}</td>
                            <td>{frappe.utils.formatdate(policy.policy_end_date)}</td>
                            <td class="{status_class}">{status_text}</td>
                        </tr>
            """
        
        message += """
                    </tbody>
                </table>
                
                <div style="margin-top: 30px; padding: 15px; background-color: #e7f3ff; border-left: 4px solid #2e86de;">
                    <h4 style="margin-top: 0;">📋 Action Items:</h4>
                    <ul>
                        <li>Review each policy for coverage adequacy</li>
                        <li>Contact insurance providers for renewal quotes</li>
                        <li>Compare premiums and coverage options</li>
                        <li>Process renewals before expiry dates</li>
                        <li>Update asset records with new policy details</li>
                    </ul>
                </div>
                
                <p style="margin-top: 20px;">If you have any questions or need assistance, please contact your administrator.</p>
                
                <p>Best regards,<br>
                <strong>Asset Management System</strong></p>
            </div>
            
            <div class="footer">
                <p>This is an automated email. Please do not reply directly to this message.</p>
                <p>© """ + str(frappe.utils.nowdate().year) + f""" {company}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=f"🛡️ Insurance Renewal Due - {company} ({len(policies)} {'policy' if len(policies) == 1 else 'policies'})",
                message=message,
                delayed=False
            )
        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title="Insurance Reminder Email Failed"
            )


@frappe.whitelist()
def get_insurance_summary(asset=None, company=None):
    """Get insurance summary statistics"""
    filters = {"docstatus": 1}
    
    if asset:
        filters["asset"] = asset
    
    if company:
        filters["company"] = company
    
    # Get active policies
    active_policies = frappe.db.count("Fixed Asset Insurance", {
        **filters,
        "policy_status": "Active"
    })
    
    # Get expiring soon
    expiring_soon = frappe.db.count("Fixed Asset Insurance", {
        **filters,
        "policy_status": "Expiring Soon"
    })
    
    # Get total sum insured
    total_insured = frappe.db.sql("""
        SELECT SUM(sum_insured) as total
        FROM `tabFixed Asset Insurance`
        WHERE docstatus = 1
        AND policy_status = 'Active'
        {conditions}
    """.format(
        conditions=" AND company = %(company)s" if company else ""
    ), {"company": company}, as_dict=True)
    
    # Get total premiums paid
    total_premiums = frappe.db.sql("""
        SELECT SUM(premium_amount) as total
        FROM `tabFixed Asset Insurance`
        WHERE docstatus = 1
        {conditions}
    """.format(
        conditions=" AND company = %(company)s" if company else ""
    ), {"company": company}, as_dict=True)
    
    return {
        "active_policies": active_policies,
        "expiring_soon": expiring_soon,
        "total_sum_insured": total_insured[0].total if total_insured else 0,
        "total_premiums": total_premiums[0].total if total_premiums else 0
    }