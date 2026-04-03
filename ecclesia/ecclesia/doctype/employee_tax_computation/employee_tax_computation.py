# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, fmt_money
import json

# 2026 Tax Brackets (Nigeria Tax Act 2025)
TAX_BRACKETS_2026 = [
    {"from": 0, "to": 800000, "rate": 0, "desc": "First ₦800,000"},
    {"from": 800000, "to": 3000000, "rate": 15, "desc": "Next ₦2,200,000"},
    {"from": 3000000, "to": 12000000, "rate": 18, "desc": "Next ₦9,000,000"},
    {"from": 12000000, "to": 25000000, "rate": 21, "desc": "Next ₦13,000,000"},
    {"from": 25000000, "to": 50000000, "rate": 23, "desc": "Next ₦25,000,000"},
    {"from": 50000000, "to": 0, "rate": 25, "desc": "Above ₦50,000,000"}
]

# Deduction Types Configuration
DEDUCTION_TYPES = [
    "Pension Contribution",
    "NHF Contribution", 
    "NHIS Contribution",
    "Life Insurance Premium",
    "Rent Relief",
    "Other Deductions"
]


class EmployeeTaxComputation(Document):
    """Employee Tax Computation DocType Controller"""
    
    def validate(self):
        """Main validation - calculate tax components WITHOUT touching deductions"""
        # Calculate total deductions from child table (already set by JS)
        self.calculate_total_deductions()
        self.calculate_total_benefits()
        self.calculate_taxable_income()
        self.calculate_tax_bands()
        self.calculate_final_tax()
        self.update_status()
    
    def on_submit(self):
        """Actions on submit"""
        self.status = "Submitted"
    
    def on_cancel(self):
        """Actions on cancel"""
        self.status = "Cancelled"
    
    def calculate_total_deductions(self):
        """Calculate total from statutory_deductions child table"""
        total = 0
        for deduction in self.statutory_deductions or []:
            total += flt(deduction.deduction_amount)
        
        self.total_deductions = total
        self.total_statutory_deductions = total
        self.step_1_amount = flt(self.annual_gross_income)
        self.step_2_amount = total
    
    def calculate_total_benefits(self):
        """Calculate total from benefits_in_kind child table"""
        total = 0
        for benefit in self.benefits_in_kind or []:
            total += flt(benefit.taxable_value)
        
        self.total_bik = total
        self.total_benefits_in_kind = total
        self.step_5_amount = total
    
    def calculate_taxable_income(self):
        """Step 3: Calculate Taxable Income (Gross - Deductions + Benefits in Kind)"""
        # CORRECT FORMULA: Taxable Income = Gross Income - Deductions + Benefits in Kind
        taxable = flt(self.annual_gross_income) - flt(self.total_deductions) + flt(self.total_benefits_in_kind)
        self.annual_taxable_income = max(taxable, 0)
        self.step_3_amount = self.annual_taxable_income
    
    def calculate_tax_bands(self):
        """Step 4: Apply 2026 progressive tax rates"""
        taxable_income = flt(self.annual_taxable_income)
        
        # Clear existing tax slabs
        self.tax_slabs = []
        
        if taxable_income <= 0:
            self.step_4_amount = 0
            return
        
        total_tax = 0
        remaining_income = taxable_income
        
        for bracket in TAX_BRACKETS_2026:
            if remaining_income <= 0:
                break
            
            bracket_from = bracket["from"]
            bracket_to = bracket["to"] if bracket["to"] > 0 else float('inf')
            rate = bracket["rate"]
            
            # Calculate income in this bracket
            if bracket_to == float('inf'):
                bracket_size = remaining_income
            else:
                bracket_size = bracket_to - bracket_from
            
            income_in_bracket = min(remaining_income, bracket_size)
            
            if income_in_bracket > 0:
                # Calculate tax for this bracket
                tax_in_bracket = income_in_bracket * (rate / 100)
                total_tax += tax_in_bracket
                
                # Add to tax slab table
                self.append("tax_slabs", {
                    "tax_level_description": bracket["desc"],
                    "tax_level_amount": income_in_bracket,
                    "tax_rate": rate,
                    "tax_amount": tax_in_bracket,
                    "cum_amount": total_tax
                })
                
                remaining_income -= income_in_bracket
        
        self.step_4_amount = total_tax
        self._tax_from_bands = total_tax
    
    def calculate_final_tax(self):
        """Calculate final tax payable"""
        # Tax on taxable income from bands
        tax_from_bands = flt(getattr(self, '_tax_from_bands', 0))
        
        # Tax on benefits in kind - already included in taxable income calculation
        # So we don't need to add extra tax for benefits
        self.annual_tax_payable = tax_from_bands
        
        # Monthly tax (PAYE)
        self.monthly_tax_payable = self.annual_tax_payable / 12 if self.annual_tax_payable > 0 else 0
        
        # Effective tax rate
        gross_income = flt(self.annual_gross_income)
        self.effective_tax_rate = (self.annual_tax_payable / gross_income * 100) if gross_income > 0 else 0
        
        # Calculate net income
        self.net_annual_income = gross_income - self.annual_tax_payable
        self.net_monthly_income = self.net_annual_income / 12 if self.net_annual_income > 0 else 0
    
    def update_status(self):
        """Update document status"""
        if self.docstatus == 1:
            self.status = "Submitted"
        elif self.docstatus == 2:
            self.status = "Cancelled"
        else:
            self.status = "Draft"


# Helper Functions
def get_tax_settings():
    """Get tax settings with defaults"""
    try:
        settings = frappe.get_single("Tax Settings")
        return {
            'pension_rate': flt(settings.pension_rate, 8),
            'nhf_rate': flt(settings.nhf_rate, 2.5),
            'nhis_rate': flt(settings.nhis_rate, 1.75),
            'life_insurance_cap': flt(settings.life_insurance_cap, 100000),
            'rent_relief_rate': flt(settings.rent_relief_rate, 20),
            'rent_relief_cap': flt(settings.rent_relief_cap, 500000)
        }
    except:
        # Return defaults if Tax Settings doesn't exist
        return {
            'pension_rate': 8,
            'nhf_rate': 2.5,
            'nhis_rate': 1.75,
            'life_insurance_cap': 100000,
            'rent_relief_rate': 20,
            'rent_relief_cap': 500000
        }


def calculate_tax_on_income(income):
    """Helper function to calculate tax on any income amount"""
    total_tax = 0
    remaining = flt(income)
    
    for bracket in TAX_BRACKETS_2026:
        if remaining <= 0:
            break
        
        bracket_from = bracket["from"]
        bracket_to = bracket["to"] if bracket["to"] > 0 else float('inf')
        rate = bracket["rate"]
        
        if bracket_to == float('inf'):
            bracket_size = remaining
        else:
            bracket_size = bracket_to - bracket_from
        
        income_in_bracket = min(remaining, bracket_size)
        
        if income_in_bracket > 0:
            total_tax += income_in_bracket * (rate / 100)
            remaining -= income_in_bracket
    
    return total_tax


# Whitelisted Methods
@frappe.whitelist()
def auto_populate_all_deductions(employee, annual_gross_income, fiscal_year=None):
    """
    Auto-populate ALL deduction types with proper rates from Tax Settings
    Returns a complete list of all deduction items
    """
    annual_gross = flt(annual_gross_income)
    tax_settings = get_tax_settings()
    
    deductions = [
        {
            "deduction_type": "Pension Contribution",
            "description": "Employee Pension Contribution",
            "basis_amount": annual_gross,
            "rate": tax_settings['pension_rate'],
            "deduction_amount": annual_gross * tax_settings['pension_rate'] / 100,
            "remarks": "Mandatory pension contribution under PRA 2014"
        },
        {
            "deduction_type": "NHF Contribution",
            "description": "National Housing Fund Contribution",
            "basis_amount": annual_gross,
            "rate": tax_settings['nhf_rate'],
            "deduction_amount": annual_gross * tax_settings['nhf_rate'] / 100,
            "remarks": "Mandatory for employees earning ₦3,000+ monthly"
        },
        {
            "deduction_type": "NHIS Contribution",
            "description": "National Health Insurance Scheme",
            "basis_amount": annual_gross,
            "rate": tax_settings['nhis_rate'],
            "deduction_amount": annual_gross * tax_settings['nhis_rate'] / 100,
            "remarks": "Mandatory health insurance contribution"
        },
        {
            "deduction_type": "Life Insurance Premium",
            "description": "Life Insurance Premium Relief",
            "basis_amount": 0,
            "rate": 0,
            "deduction_amount": 0,
            "remarks": f"Enter premium paid (Max ₦{fmt_money(tax_settings['life_insurance_cap'])})"
        },
        {
            "deduction_type": "Rent Relief",
            "description": "Rent Relief Allowance",
            "basis_amount": 0,
            "rate": tax_settings['rent_relief_rate'],
            "deduction_amount": 0,
            "remarks": f"Enter annual rent paid (Max ₦{fmt_money(tax_settings['rent_relief_cap'])} relief)"
        }
    ]
    
    return deductions


@frappe.whitelist()
def get_tax_settings_rates():
    """Get current tax settings rates for display"""
    return get_tax_settings()


@frappe.whitelist()
def auto_populate_deductions(employee, annual_gross_income):
    """Legacy function - now calls the enhanced version"""
    return auto_populate_all_deductions(employee, annual_gross_income)


@frappe.whitelist()
def get_tax_summary(name):
    """Get detailed tax summary for display"""
    doc = frappe.get_doc("Employee Tax Computation", name)
    
    # Build tax breakdown
    tax_breakdown = []
    for slab in doc.tax_slabs:
        tax_breakdown.append({
            "description": slab.tax_level_description,
            "income": slab.tax_level_amount,
            "rate": slab.tax_rate,
            "tax": slab.tax_amount,
            "cumulative": slab.cum_amount
        })
    
    # Build deductions summary
    deductions_summary = []
    for ded in doc.statutory_deductions:
        deductions_summary.append({
            "type": ded.deduction_type,
            "description": ded.description,
            "basis": ded.basis_amount,
            "rate": ded.rate,
            "amount": ded.deduction_amount,
            "remarks": ded.remarks or ""
        })
    
    # Build benefits summary
    benefits_summary = []
    for ben in doc.benefits_in_kind:
        benefits_summary.append({
            "type": ben.benefit_type,
            "description": ben.description,
            "value": ben.taxable_value,
            "remarks": ben.remarks or ""
        })
    
    # Count benefits
    benefits_count = len(doc.benefits_in_kind) if doc.benefits_in_kind else 0
    
    return {
        "employee": doc.employee,
        "employee_name": doc.employee_name,
        "tax_year": doc.fiscal_year,
        "gross_income": doc.annual_gross_income,
        "total_deductions": doc.total_deductions,
        "taxable_income": doc.annual_taxable_income,
        "total_benefits": doc.total_bik,
        "annual_tax": doc.annual_tax_payable,
        "monthly_tax": doc.monthly_tax_payable,
        "effective_rate": doc.effective_tax_rate,
        "net_annual_income": doc.net_annual_income,
        "net_monthly_income": doc.net_monthly_income,
        "tax_breakdown": tax_breakdown,
        "deductions_summary": deductions_summary,
        "benefits_summary": benefits_summary,
        "benefits_count": benefits_count
    }


@frappe.whitelist()
def quick_calculate(annual_gross, taxable_income, deductions_json="[]", benefits_json="[]"):
    """Quick tax calculation for real-time preview"""
    annual_gross = flt(annual_gross)
    taxable_income = flt(taxable_income)
    
    # Parse JSON inputs
    try:
        deductions = json.loads(deductions_json) if isinstance(deductions_json, str) else deductions_json
        benefits = json.loads(benefits_json) if isinstance(benefits_json, str) else benefits_json
    except:
        deductions = []
        benefits = []
    
    # Calculate total deductions
    deductions_total = sum([flt(d.get('deduction_amount', 0)) for d in deductions])
    
    # Calculate total benefits
    benefits_total = sum([flt(b.get('taxable_value', 0)) for b in benefits])
    
    # Use provided taxable_income or calculate it WITH BENEFITS INCLUDED
    if taxable_income <= 0:
        # CORRECTED: Include benefits in taxable income calculation
        taxable_income = max(annual_gross - deductions_total + benefits_total, 0)
    
    # Calculate tax on taxable income (which already includes benefits)
    total_tax = calculate_tax_on_income(taxable_income)
    
    # Net income
    net_annual = annual_gross - total_tax
    net_monthly = net_annual / 12
    
    return {
        "gross_income": annual_gross,
        "total_deductions": deductions_total,
        "taxable_income": taxable_income,
        "total_benefits": benefits_total,
        "tax_on_income": total_tax,
        "total_annual_tax": total_tax,
        "monthly_tax": total_tax / 12,
        "effective_rate": (total_tax / annual_gross * 100) if annual_gross > 0 else 0,
        "net_annual_income": net_annual,
        "net_monthly_income": net_monthly
    }


@frappe.whitelist()
def verify_tax_calculation(gross_income, deductions_total, benefits_total):
    """
    Verify the tax calculation formula:
    taxable_income = gross_income - deductions_total + benefits_total
    tax = calculate_tax_on_income(taxable_income)
    """
    gross_income = flt(gross_income)
    deductions_total = flt(deductions_total)
    benefits_total = flt(benefits_total)
    
    # Calculate taxable income using the correct formula
    taxable_income = gross_income - deductions_total + benefits_total
    
    # Calculate tax
    tax_amount = calculate_tax_on_income(max(taxable_income, 0))
    
    return {
        "formula": "Taxable Income = Gross Income - Deductions + Benefits in Kind",
        "calculation": f"{gross_income} - {deductions_total} + {benefits_total}",
        "taxable_income": max(taxable_income, 0),
        "tax_amount": tax_amount,
        "effective_tax_rate": (tax_amount / gross_income * 100) if gross_income > 0 else 0
    }