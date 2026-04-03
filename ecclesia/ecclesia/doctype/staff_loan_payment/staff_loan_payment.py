# -*- coding: utf-8 -*-
# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt, get_last_day, formatdate, nowdate
from erpnext.accounts.utils import get_account_currency

class StaffLoanPayment(Document):
    def validate(self):
        self.validate_dates()
        self.validate_accounts()
        
    def validate_dates(self):
        """Validate start and end dates"""
        if self.start_date and getdate(self.start_date) < getdate(self.posting_date):
            frappe.throw("Repayment Start Date cannot be before Posting Date")
    
    def validate_accounts(self):
        """Validate that required accounts are set"""
        if not self.payment_account:
            default_account = frappe.get_value("Company", self.company, "default_cash_account")
            if default_account:
                self.payment_account = default_account
        
        if not self.loan_account:
            loan_account = frappe.db.get_value(
                "Account", 
                {"account_name": ["like", "%Employee Loan%"], "company": self.company, "is_group": 0},
                "name"
            )
            if loan_account:
                self.loan_account = loan_account
    
    def on_submit(self):
        """Create Payment Entry and Additional Salary records on submit"""
        self.status = "Active"
        self.create_loan_disbursement_payment()
        self.create_additional_salary_records()
    
    def on_cancel(self):
        """Cancel related Payment Entry and Additional Salary records"""
        self.status = "Cancelled"
        self.cancel_payment_entry()
        self.cancel_additional_salary_records()
        self.cancel_interest_journal_entries()
    
    def create_loan_disbursement_payment(self):
        """Create Payment Entry for loan disbursement to employee"""
        if self.payment_entry:
            frappe.throw("Payment Entry already exists for this loan")
        
        try:
            # Get account currencies
            paid_from_currency = get_account_currency(self.payment_account)
            paid_to_currency = get_account_currency(self.loan_account)
            company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
            
            payment_entry = frappe.get_doc({
                "doctype": "Payment Entry",
                "payment_type": "Pay",
                "posting_date": self.posting_date,
                "company": self.company,
                "mode_of_payment": self.mode_of_payment or "Cash",
                "party_type": "Employee",
                "party": self.employee,
                "party_name": self.employee_name,
                "paid_from": self.payment_account,
                "paid_to": self.loan_account,
                "paid_from_account_currency": paid_from_currency,
                "paid_to_account_currency": paid_to_currency,
                "paid_amount": self.total_loan_amount,
                "received_amount": self.total_loan_amount,
                "source_exchange_rate": 1,
                "target_exchange_rate": 1,
                "reference_no": self.name,
                "reference_date": self.posting_date,
                "remarks": f"Loan disbursement for {self.loan_type} - {self.name}"
            })
            
            payment_entry.insert(ignore_permissions=True)
            payment_entry.submit()
            
            self.db_set("payment_entry", payment_entry.name)
            
            frappe.msgprint(
                f"Payment Entry {payment_entry.name} created successfully",
                alert=True,
                indicator='green'
            )
            
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Create Payment Entry Error")
            frappe.throw(f"Error creating Payment Entry: {str(e)}")
    
    def cancel_payment_entry(self):
        """Cancel the payment entry when loan is cancelled"""
        if self.payment_entry:
            try:
                payment_doc = frappe.get_doc("Payment Entry", self.payment_entry)
                if payment_doc.docstatus == 1:
                    payment_doc.cancel()
                    frappe.msgprint(f"Payment Entry {self.payment_entry} cancelled", alert=True)
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Cancel Payment Entry Error - {self.payment_entry}")
    
    def create_additional_salary_records(self):
        """Create Additional Salary records based on create_all_at_once flag"""
        if not self.loan_deduction_schedule:
            frappe.throw("Loan Deduction Schedule is empty")
        
        salary_component = self.get_or_create_salary_component()
        
        if self.create_all_at_once:
            self.create_recurring_additional_salary(salary_component)
        else:
            self.create_individual_additional_salaries(salary_component)
    
    def get_or_create_salary_component(self):
        """Get or create salary component for loan deduction"""
        component_name = f"Loan Deduction - {self.loan_type}"
        
        if not frappe.db.exists("Salary Component", component_name):
            salary_component = frappe.get_doc({
                "doctype": "Salary Component",
                "salary_component": component_name,
                "salary_component_abbr": "LD",
                "type": "Deduction",
                "description": f"Loan Deduction for {self.loan_type}"
            })
            salary_component.insert(ignore_permissions=True)
            return component_name
        
        return component_name
    
    def create_recurring_additional_salary(self, salary_component):
        """Create one recurring Additional Salary for all installments"""
        try:
            # Get the monthly deduction (principal + interest if applicable)
            first_installment = self.loan_deduction_schedule[0]
            monthly_amount = flt(first_installment.deduction_amount)
            
            additional_salary = frappe.get_doc({
                "doctype": "Additional Salary",
                "employee": self.employee,
                "employee_name": self.employee_name,
                "company": self.company,
                "salary_component": salary_component,
                "amount": monthly_amount,
                "payroll_date": self.start_date,
                "from_date": self.start_date,
                "to_date": self.end_date,
                "is_recurring": 1,
                "overwrite_salary_structure_amount": 0,
                "ref_doctype": self.doctype,
                "ref_docname": self.name
            })
            
            additional_salary.insert(ignore_permissions=True)
            additional_salary.submit()
            
            for row in self.loan_deduction_schedule:
                row.db_set("additional_salary", additional_salary.name, update_modified=False)
            
            frappe.msgprint(f"Recurring Additional Salary {additional_salary.name} created", alert=True)
            
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Create Recurring Additional Salary Error")
            frappe.throw(f"Error creating Additional Salary: {str(e)}")
    
    def create_individual_additional_salaries(self, salary_component):
        """Create individual Additional Salary for each installment"""
        created_count = 0
        
        for idx, schedule_row in enumerate(self.loan_deduction_schedule, start=1):
            try:
                additional_salary = frappe.get_doc({
                    "doctype": "Additional Salary",
                    "employee": self.employee,
                    "employee_name": self.employee_name,
                    "company": self.company,
                    "salary_component": salary_component,
                    "amount": schedule_row.deduction_amount,
                    "payroll_date": schedule_row.payment_date,
                    "from_date": schedule_row.payment_date,
                    "to_date": schedule_row.payment_date,
                    "is_recurring": 0,
                    "overwrite_salary_structure_amount": 0,
                    "ref_doctype": self.doctype,
                    "ref_docname": self.name
                })
                
                additional_salary.insert(ignore_permissions=True)
                additional_salary.submit()
                
                schedule_row.db_set("additional_salary", additional_salary.name, update_modified=False)
                created_count += 1
                
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Create Additional Salary Error - Row {idx}")
        
        if created_count > 0:
            frappe.msgprint(f"{created_count} Additional Salary records created", alert=True, indicator='green')
    
    def cancel_additional_salary_records(self):
        """Cancel all related Additional Salary records"""
        additional_salaries = frappe.get_all(
            "Additional Salary",
            filters={
                "ref_doctype": self.doctype,
                "ref_docname": self.name,
                "docstatus": 1
            },
            pluck="name"
        )
        
        for salary_name in additional_salaries:
            try:
                additional_salary = frappe.get_doc("Additional Salary", salary_name)
                additional_salary.cancel()
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Cancel Additional Salary Error - {salary_name}")
    
    def cancel_interest_journal_entries(self):
        """Cancel all interest journal entries"""
        if not self.apply_interest:
            return
            
        for row in self.loan_deduction_schedule:
            if row.interest_journal_entry:
                try:
                    journal_entry = frappe.get_doc("Journal Entry", row.interest_journal_entry)
                    if journal_entry.docstatus == 1:
                        journal_entry.cancel()
                except Exception as e:
                    frappe.log_error(
                        frappe.get_traceback(), 
                        f"Cancel Interest Journal Entry Error - {row.interest_journal_entry}"
                    )


@frappe.whitelist()
def update_loan_repayment_status(loan_payment_name):
    """
    Update loan repayment status based on salary slips
    and create interest journal entries if applicable
    """
    doc = frappe.get_doc("Staff Loan Payment", loan_payment_name)
    
    for row in doc.loan_deduction_schedule:
        if row.additional_salary and not row.is_paid:
            # Check if salary slip exists for this period
            salary_slips = frappe.get_all(
                "Salary Slip",
                filters={
                    "employee": doc.employee,
                    "start_date": ["<=", row.payment_date],
                    "end_date": [">=", row.payment_date],
                    "docstatus": 1
                },
                pluck="name"
            )
            
            if salary_slips:
                # Mark as paid
                row.db_set("is_paid", 1, update_modified=False)
                row.db_set("payment_reference", ", ".join(salary_slips), update_modified=False)
                
                # Create interest journal entry if applicable
                if doc.apply_interest and flt(row.interest_amount) > 0 and not row.interest_journal_entry:
                    create_interest_journal_entry(doc, row)
    
    # Recalculate totals
    total_deducted = sum([flt(d.deduction_amount) for d in doc.loan_deduction_schedule if d.is_paid])
    doc.db_set("total_deducted_amount", total_deducted, update_modified=False)
    doc.db_set("outstanding_amount", flt(doc.total_loan_amount) - flt(total_deducted), update_modified=False)
    
    # Check if loan is fully paid
    if flt(doc.outstanding_amount) == 0:
        doc.db_set("status", "Completed", update_modified=False)
        frappe.msgprint(f"Loan {doc.name} has been fully repaid", alert=True, indicator='green')
    
    return doc


def create_interest_journal_entry(loan_doc, schedule_row):
    """
    Create journal entry to recognize interest income
    This is called when a salary slip is processed with the loan deduction
    """
    try:
        # Get interest income account
        interest_income_account = get_interest_income_account(loan_doc.company)
        
        if not interest_income_account:
            frappe.log_error(
                "Interest Income account not found",
                f"Create Interest JE Error - {loan_doc.name}"
            )
            return None
        
        # Create Journal Entry
        journal_entry = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": schedule_row.payment_date,
            "company": loan_doc.company,
            "user_remark": f"Interest income on loan {loan_doc.name} for {formatdate(schedule_row.payment_date)}",
            "accounts": [
                {
                    "account": loan_doc.loan_account,
                    "debit_in_account_currency": flt(schedule_row.interest_amount),
                    "party_type": "Employee",
                    "party": loan_doc.employee,
                    "reference_type": loan_doc.doctype,
                    "reference_name": loan_doc.name
                },
                {
                    "account": interest_income_account,
                    "credit_in_account_currency": flt(schedule_row.interest_amount),
                    "reference_type": loan_doc.doctype,
                    "reference_name": loan_doc.name
                }
            ]
        })
        
        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()
        
        schedule_row.db_set("interest_journal_entry", journal_entry.name, update_modified=False)
        
        frappe.msgprint(f"Interest Journal Entry {journal_entry.name} created", alert=True)
        
        return journal_entry.name
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Create Interest Journal Entry Error - {schedule_row.name}")
        return None


def get_interest_income_account(company):
    """Get interest income account for the company"""
    account = frappe.db.get_value(
        "Account",
        {
            "account_name": ["like", "%Interest Income%"],
            "company": company,
            "is_group": 0,
            "root_type": "Income"
        },
        "name"
    )
    
    if not account:
        # Try alternate names
        account = frappe.db.get_value(
            "Account",
            {
                "account_name": ["in", ["Interest Income", "Income from Interest"]],
                "company": company,
                "is_group": 0
            },
            "name"
        )
    
    return account


#just added

def update_loan_on_salary_submit(doc, method):
    """
    Hook function that runs when a Salary Slip is submitted
    Automatically updates loan repayment status
    """
    if not doc.employee:
        return
    
    # Get all active loans for this employee
    active_loans = frappe.get_all(
        "Staff Loan Payment",
        filters={
            "employee": doc.employee,
            "docstatus": 1,
            "status": "Active"
        },
        pluck="name"
    )
    
    # Update payment status for each loan
    for loan_name in active_loans:
        try:
            # Check if this salary slip period matches any loan installment
            loan_doc = frappe.get_doc("Staff Loan Payment", loan_name)
            
            for row in loan_doc.loan_deduction_schedule:
                if row.additional_salary and not row.is_paid:
                    # Check if this salary slip covers the payment period
                    if (doc.start_date <= getdate(row.payment_date) <= doc.end_date):
                        # Mark as paid
                        row.db_set("is_paid", 1, update_modified=False)
                        row.db_set("payment_reference", doc.name, update_modified=False)
                        
                        # Create interest journal entry if applicable
                        if loan_doc.apply_interest and flt(row.interest_amount) > 0 and not row.interest_journal_entry:
                            create_interest_journal_entry(loan_doc, row)
            
            # Recalculate totals
            total_deducted = sum([flt(d.deduction_amount) for d in loan_doc.loan_deduction_schedule if d.is_paid])
            loan_doc.db_set("total_deducted_amount", total_deducted, update_modified=False)
            loan_doc.db_set("outstanding_amount", flt(loan_doc.total_loan_amount) - flt(total_deducted), update_modified=False)
            
            # Check if loan is fully paid
            if flt(loan_doc.outstanding_amount) == 0:
                loan_doc.db_set("status", "Completed", update_modified=False)
                frappe.msgprint(
                    f"Loan {loan_doc.name} has been fully repaid!",
                    alert=True,
                    indicator='green'
                )
        
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Update Loan on Salary Submit Error - {loan_name}"
            )



@frappe.whitelist()
def get_loan_balance(employee, loan_type=None):
    """Get outstanding loan balance for an employee"""
    filters = {
        "employee": employee,
        "docstatus": 1,
        "status": ["in", ["Active"]]
    }
    
    if loan_type:
        filters["loan_type"] = loan_type
    
    loans = frappe.get_all(
        "Staff Loan Payment",
        filters=filters,
        fields=["name", "loan_type", "total_loan_amount", "outstanding_amount", "payment_entry"]
    )
    
    return loans


@frappe.whitelist()
def process_monthly_loan_repayments():
    """
    Scheduled function to process monthly loan repayments
    Add this to your hooks.py as a daily scheduled task
    """
    active_loans = frappe.get_all(
        "Staff Loan Payment",
        filters={
            "docstatus": 1,
            "status": "Active"
        },
        pluck="name"
    )
    
    processed_count = 0
    for loan_name in active_loans:
        try:
            update_loan_repayment_status(loan_name)
            processed_count += 1
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Process Monthly Repayment Error - {loan_name}")
    
    return f"Processed {processed_count} loans"


@frappe.whitelist()
def create_interest_income_account(company):
    """
    Helper function to create Interest Income account if it doesn't exist
    Can be called from the UI if needed
    """
    if not company:
        frappe.throw("Company is required")
    
    # Check if account already exists
    existing_account = get_interest_income_account(company)
    if existing_account:
        return existing_account
    
    try:
        # Get the parent income account
        parent_account = frappe.db.get_value(
            "Account",
            {
                "account_name": "Indirect Income",
                "company": company,
                "is_group": 1
            },
            "name"
        )
        
        if not parent_account:
            parent_account = frappe.db.get_value(
                "Account",
                {
                    "root_type": "Income",
                    "company": company,
                    "is_group": 1
                },
                "name"
            )
        
        if not parent_account:
            frappe.throw("Cannot find suitable parent account for Interest Income")
        
        # Create the account
        account = frappe.get_doc({
            "doctype": "Account",
            "account_name": "Interest Income",
            "parent_account": parent_account,
            "company": company,
            "root_type": "Income",
            "account_type": "",
            "is_group": 0
        })
        
        account.insert(ignore_permissions=True)
        
        frappe.msgprint(f"Interest Income account created: {account.name}", alert=True, indicator='green')
        
        return account.name
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Interest Income Account Error")
        frappe.throw(f"Error creating Interest Income account: {str(e)}")

