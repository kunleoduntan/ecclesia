# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint


class FixedAssetCategory(Document):
    def validate(self):
        """Validate asset category settings"""
        self.validate_depreciation_settings()
        self.validate_accounts()
        self.validate_prefix()
        self.validate_hierarchy()
    
    def before_save(self):
        """Before save operations"""
        self.set_next_asset_number()
    
    def validate_depreciation_settings(self):
        """Validate depreciation related settings"""
        if self.enable_depreciation:
            if not self.depreciation_method:
                frappe.throw(_("Depreciation Method is required when depreciation is enabled"))
            
            if not self.total_number_of_depreciations:
                frappe.throw(_("Total Number of Depreciations is required"))
            
            if not self.frequency_of_depreciation:
                frappe.throw(_("Frequency of Depreciation is required"))
            
            if flt(self.total_number_of_depreciations) <= 0:
                frappe.throw(_("Total Number of Depreciations must be greater than 0"))
            
            if cint(self.frequency_of_depreciation) not in [1, 3, 6, 12]:
                frappe.throw(_("Frequency of Depreciation must be 1, 3, 6, or 12 months"))
            
            # Validate depreciation rate for WDV methods
            if self.depreciation_method in ["Written Down Value", "Double Declining Balance"]:
                if not self.depreciation_rate or flt(self.depreciation_rate) <= 0:
                    frappe.throw(_("Depreciation Rate is required for {0} method").format(self.depreciation_method))
                
                if flt(self.depreciation_rate) > 100:
                    frappe.throw(_("Depreciation Rate cannot exceed 100%"))
            
            # Validate residual value
            if flt(self.residual_value_percentage) < 0 or flt(self.residual_value_percentage) >= 100:
                frappe.throw(_("Residual Value Percentage must be between 0 and 100"))
    
    def validate_accounts(self):
        """Validate account mappings"""
        if not self.fixed_asset_account:
            frappe.throw(_("Fixed Asset Account is required"))
        
        # Validate account types
        self.validate_account_type(self.fixed_asset_account, ["Fixed Asset", "Asset"])
        
        if self.enable_depreciation:
            if not self.accumulated_depreciation_account:
                frappe.throw(_("Accumulated Depreciation Account is required when depreciation is enabled"))
            
            if not self.depreciation_expense_account:
                frappe.throw(_("Depreciation Expense Account is required when depreciation is enabled"))
            
            self.validate_account_type(self.accumulated_depreciation_account, ["Accumulated Depreciation"])
            self.validate_account_type(self.depreciation_expense_account, ["Depreciation", "Expense Account"])
        
        # Validate optional accounts if provided
        if self.capital_work_in_progress_account:
            self.validate_account_type(self.capital_work_in_progress_account, ["Capital Work in Progress"])
        
        if self.asset_disposal_account:
            self.validate_account_type(self.asset_disposal_account, ["Asset Received But Not Billed"])
        
        # Validate all accounts belong to same company (if we add company field later)
        self.validate_accounts_company()
    
    def validate_account_type(self, account, valid_types):
        """Validate that account is of correct type"""
        if not account:
            return
        
        account_type = frappe.db.get_value("Account", account, "account_type")
        root_type = frappe.db.get_value("Account", account, "root_type")
        
        # Check if account type matches any of the valid types
        valid = False
        for vtype in valid_types:
            if vtype in [account_type, root_type]:
                valid = True
                break
        
        if not valid:
            frappe.throw(
                _("Account {0} must be of type {1}. Current type: {2}").format(
                    account,
                    " or ".join(valid_types),
                    account_type or root_type
                )
            )
    
    def validate_accounts_company(self):
        """Ensure all accounts belong to the same company"""
        accounts = [
            self.fixed_asset_account,
            self.accumulated_depreciation_account,
            self.depreciation_expense_account,
            self.capital_work_in_progress_account,
            self.asset_disposal_account,
            self.gain_on_disposal_account,
            self.loss_on_disposal_account,
            self.revaluation_reserve_account,
            self.revaluation_surplus_account,
            self.revaluation_loss_account
        ]
        
        # Filter out empty accounts
        accounts = [acc for acc in accounts if acc]
        
        if not accounts:
            return
        
        # Get companies for all accounts
        companies = set()
        for account in accounts:
            company = frappe.db.get_value("Account", account, "company")
            if company:
                companies.add(company)
        
        if len(companies) > 1:
            frappe.throw(_("All accounts must belong to the same company"))
    
    def validate_prefix(self):
        """Validate asset code prefix"""
        if not self.asset_code_prefix:
            frappe.throw(_("Asset Code Prefix is required"))
        
        # Check if prefix already exists for another category
        existing = frappe.db.sql("""
            SELECT name 
            FROM `tabFixed Asset Category` 
            WHERE asset_code_prefix = %s 
            AND name != %s
        """, (self.asset_code_prefix, self.name))
        
        if existing:
            frappe.msgprint(
                _("Warning: Asset Code Prefix '{0}' is already used by category '{1}'").format(
                    self.asset_code_prefix,
                    existing[0][0]
                ),
                alert=True
            )
    
    def validate_hierarchy(self):
        """Validate parent-child hierarchy"""
        if self.parent_category:
            # Check for circular reference
            if self.parent_category == self.name:
                frappe.throw(_("Category cannot be its own parent"))
            
            # Check if parent exists
            if not frappe.db.exists("Fixed Asset Category", self.parent_category):
                frappe.throw(_("Parent Category {0} does not exist").format(self.parent_category))
            
            # Check if parent is a group
            parent_doc = frappe.get_doc("Fixed Asset Category", self.parent_category)
            if not parent_doc.is_group:
                frappe.throw(_("Parent Category must be a Group"))
            
            # Check for circular hierarchy
            self.check_circular_hierarchy(self.parent_category, [self.name])
        
        if self.is_group:
            # Check if category has any assets
            asset_count = frappe.db.count("Fixed Asset", {"asset_category": self.name})
            if asset_count > 0:
                frappe.throw(
                    _("Cannot convert to Group. This category has {0} asset(s) assigned to it").format(asset_count)
                )
    
    def check_circular_hierarchy(self, parent, visited):
        """Check for circular reference in hierarchy"""
        if parent in visited:
            frappe.throw(_("Circular reference detected in category hierarchy"))
        
        visited.append(parent)
        
        parent_category = frappe.db.get_value("Fixed Asset Category", parent, "parent_category")
        if parent_category:
            self.check_circular_hierarchy(parent_category, visited)
    
    def set_next_asset_number(self):
        """Initialize next asset number if not set"""
        if not self.next_asset_number:
            self.next_asset_number = self.asset_code_series_start or 1


# Whitelisted methods

@frappe.whitelist()
def get_next_asset_code(category):
    """Get next asset code for a category"""
    
    if not category:
        frappe.throw(_("Category is required"))
    
    category_doc = frappe.get_doc("Fixed Asset Category", category)
    
    # Get next number
    next_number = category_doc.next_asset_number or category_doc.asset_code_series_start or 1
    
    # Generate code based on format
    code_format = category_doc.asset_code_format or "PREFIX-#####"
    prefix = category_doc.asset_code_prefix
    
    if code_format == "PREFIX-####":
        asset_code = f"{prefix}{str(next_number).zfill(4)}"
    elif code_format == "PREFIX-#####":
        asset_code = f"{prefix}{str(next_number).zfill(5)}"
    elif code_format == "PREFIX-######":
        asset_code = f"{prefix}{str(next_number).zfill(6)}"
    elif code_format == "PREFIX-YYYY-####":
        from frappe.utils import nowdate
        year = nowdate()[:4]
        asset_code = f"{prefix}{year}-{str(next_number).zfill(4)}"
    elif code_format == "PREFIX-YYYY-#####":
        from frappe.utils import nowdate
        year = nowdate()[:4]
        asset_code = f"{prefix}{year}-{str(next_number).zfill(5)}"
    else:
        asset_code = f"{prefix}{str(next_number).zfill(5)}"
    
    # Increment next number
    category_doc.db_set("next_asset_number", next_number + 1, update_modified=False)
    
    return asset_code


@frappe.whitelist()
def get_category_defaults(category):
    """Get default settings for a category"""
    
    if not category:
        return {}
    
    category_doc = frappe.get_doc("Fixed Asset Category", category)
    
    return {
        "enable_depreciation": category_doc.enable_depreciation,
        "depreciation_method": category_doc.depreciation_method,
        "depreciation_rate": category_doc.depreciation_rate,
        "total_number_of_depreciations": category_doc.total_number_of_depreciations,
        "frequency_of_depreciation": category_doc.frequency_of_depreciation,
        "residual_value_percentage": category_doc.residual_value_percentage,
        "fixed_asset_account": category_doc.fixed_asset_account,
        "accumulated_depreciation_account": category_doc.accumulated_depreciation_account,
        "depreciation_expense_account": category_doc.depreciation_expense_account,
        "capital_work_in_progress_account": category_doc.capital_work_in_progress_account,
        "depreciation_start_from": category_doc.depreciation_start_from,
        "calculate_depreciation_on_pro_rata_basis": category_doc.calculate_depreciation_on_pro_rata_basis,
        "auto_create_depreciation_schedule": category_doc.auto_create_depreciation_schedule,
        "typical_useful_life_years": category_doc.typical_useful_life_years,
        "warranty_period_months": category_doc.warranty_period_months,
        "insurance_required": category_doc.insurance_required,
        "minimum_insurance_amount": category_doc.minimum_insurance_amount
    }


@frappe.whitelist()
def get_depreciation_settings(category):
    """Get depreciation settings for a category"""
    
    if not category:
        return {}
    
    settings = frappe.db.get_value("Fixed Asset Category", category, [
        "enable_depreciation",
        "depreciation_method",
        "depreciation_rate",
        "total_number_of_depreciations",
        "frequency_of_depreciation",
        "residual_value_percentage"
    ], as_dict=1)
    
    return settings or {}


@frappe.whitelist()
def get_account_defaults(category):
    """Get account defaults for a category"""
    
    if not category:
        return {}
    
    accounts = frappe.db.get_value("Fixed Asset Category", category, [
        "fixed_asset_account",
        "accumulated_depreciation_account",
        "depreciation_expense_account",
        "capital_work_in_progress_account",
        "asset_disposal_account",
        "gain_on_disposal_account",
        "loss_on_disposal_account",
        "revaluation_reserve_account",
        "revaluation_surplus_account",
        "revaluation_loss_account"
    ], as_dict=1)
    
    return accounts or {}


@frappe.whitelist()
def get_category_summary():
    """Get summary of all asset categories"""
    
    summary = frappe.db.sql("""
        SELECT 
            cat.name as category,
            cat.category_code,
            cat.enable_depreciation,
            cat.depreciation_method,
            COUNT(asset.name) as total_assets,
            SUM(asset.gross_purchase_amount) as total_value,
            SUM(asset.accumulated_depreciation) as total_depreciation,
            SUM(asset.current_value) as total_current_value
        FROM 
            `tabFixed Asset Category` cat
        LEFT JOIN 
            `tabFixed Asset` asset ON asset.asset_category = cat.name AND asset.docstatus = 1
        GROUP BY 
            cat.name
        ORDER BY 
            cat.name
    """, as_dict=1)
    
    return summary


@frappe.whitelist()
def validate_asset_code_unique(asset_code, exclude_asset=None):
    """Check if asset code is unique"""
    
    filters = {"asset_code": asset_code}
    
    if exclude_asset:
        filters["name"] = ["!=", exclude_asset]
    
    exists = frappe.db.exists("Fixed Asset", filters)
    
    return not exists