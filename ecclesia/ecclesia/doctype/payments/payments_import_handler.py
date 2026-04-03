# payments_import_handler.py
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
import json


@frappe.whitelist()
def get_payments_import_template():
    """Generate import template for Payments with headers and sample data"""
    
    # Define template columns based on mandatory and key fields
    template_columns = [
        # Transaction Header
        "Transaction Date*",
        "Transaction Type*",
        "Company*",
        "Payment Status",
        
        # Beneficiary Information
        "Supplier ID",
        "Beneficiary Name",
        "Customer ID",
        
        # Transaction Options
        "Create Accounting Entries",
        "Deduct WHT",
        "Amortize Expense",
        "Multiple Line Items",
        "Shared Cost Allocation",
        "Inter-Company Transaction",
        
        # Accounting Dimensions
        "Branch",
        "Nature of Expense",
        "Cost Center",
        "Department",
        "Project",
        
        # Currency & Exchange
        "Payment Currency*",
        "Exchange Rate",
        
        # Payment Amount
        "Amount Paid (NGN)",
        "Amount Paid (Foreign Currency)",
        
        # Payment Details
        "Mode of Payment*",
        "Cheque/Reference No*",
        "Account To Debit",
        "Transaction Purpose*",
        
        # WHT Details
        "WHT Rate (%)",
        "WHT Account",
        
        # Banking Details
        "Bank Account*",
        "Cash Flow Classification*",
        "Approval Document Reference",
        
        # Approval/Signatures
        "Issued By",
        "Issue Date",
        "Authorised By",
        "Authorization Date",
        "Approved By",
        "Approval Date"
    ]
    
    # Sample data row
    sample_data = [
        "2025-01-21",  # Transaction Date
        "Supplier Payment",  # Transaction Type
        "Your Company Name",  # Company
        "Draft",  # Payment Status
        "SUPP-00001",  # Supplier ID
        "",  # Beneficiary Name (for Expense Payment)
        "",  # Customer ID
        "1",  # Create Accounting Entries (1=Yes, 0=No)
        "0",  # Deduct WHT
        "0",  # Amortize Expense
        "0",  # Multiple Line Items
        "0",  # Shared Cost Allocation
        "0",  # Inter-Company Transaction
        "Head Office",  # Branch
        "",  # Nature of Expense
        "Main - YC",  # Cost Center
        "Accounts",  # Department
        "",  # Project
        "NGN",  # Payment Currency
        "1",  # Exchange Rate
        "500000",  # Amount Paid (NGN)
        "",  # Amount Paid (Foreign Currency)
        "Bank Draft",  # Mode of Payment
        "CHQ-001",  # Cheque/Reference No
        "",  # Account To Debit
        "Payment for office supplies",  # Transaction Purpose
        "",  # WHT Rate (%)
        "",  # WHT Account
        "FCMB - YC",  # Bank Account
        "Supplier payments",  # Cash Flow Classification
        "",  # Approval Document Reference
        "[email protected]",  # Issued By
        "2025-01-21",  # Issue Date
        "",  # Authorised By
        "",  # Authorization Date
        "",  # Approved By
        ""  # Approval Date
    ]
    
    return {
        "columns": template_columns,
        "sample_data": sample_data
    }
    


@frappe.whitelist()
def validate_payments_import(data):
    """Validate imported payments data before creating records"""
    
    errors = []
    validated_data = []
    
    for idx, row in enumerate(data, start=2):  # Start from row 2 (after header)
        row_errors = []
        
        # Validate mandatory fields
        if not row.get("Transaction Date"):
            row_errors.append(f"Row {idx}: Transaction Date is mandatory")
            
        if not row.get("Transaction Type"):
            row_errors.append(f"Row {idx}: Transaction Type is mandatory")
        elif row.get("Transaction Type") not in [
            "Supplier Payment", "Expense Payment", "Transfer Out", 
            "Supplier Refunds", "Payment Request", "Maintenance Request"
        ]:
            row_errors.append(f"Row {idx}: Invalid Transaction Type")
            
        if not row.get("Company"):
            row_errors.append(f"Row {idx}: Company is mandatory")
        else:
            # Validate company exists
            if not frappe.db.exists("Company", row.get("Company")):
                row_errors.append(f"Row {idx}: Company '{row.get('Company')}' does not exist")
                
        if not row.get("Payment Currency"):
            row_errors.append(f"Row {idx}: Payment Currency is mandatory")
            
        if not row.get("Mode of Payment"):
            row_errors.append(f"Row {idx}: Mode of Payment is mandatory")
            
        if not row.get("Cheque/Reference No"):
            row_errors.append(f"Row {idx}: Cheque/Reference No is mandatory")
            
        if not row.get("Transaction Purpose"):
            row_errors.append(f"Row {idx}: Transaction Purpose is mandatory")
            
        if not row.get("Bank Account"):
            row_errors.append(f"Row {idx}: Bank Account is mandatory")
            
        if not row.get("Cash Flow Classification"):
            row_errors.append(f"Row {idx}: Cash Flow Classification is mandatory")
        
        # Validate transaction type specific requirements
        trans_type = row.get("Transaction Type")
        
        if trans_type == "Supplier Payment":
            if not row.get("Supplier ID"):
                row_errors.append(f"Row {idx}: Supplier ID is required for Supplier Payment")
            elif not frappe.db.exists("Supplier", row.get("Supplier ID")):
                row_errors.append(f"Row {idx}: Supplier '{row.get('Supplier ID')}' does not exist")
                
        elif trans_type == "Expense Payment":
            if not row.get("Account To Debit"):
                row_errors.append(f"Row {idx}: Account To Debit is required for Expense Payment")
            if not row.get("Cost Center"):
                row_errors.append(f"Row {idx}: Cost Center is required for Expense Payment")
            if not row.get("Beneficiary Name"):
                row_errors.append(f"Row {idx}: Beneficiary Name is required for Expense Payment")
                
        elif trans_type == "Transfer Out":
            if not row.get("Account To Debit"):
                row_errors.append(f"Row {idx}: Account To Debit is required for Transfer Out")
            if not row.get("Beneficiary Name"):
                row_errors.append(f"Row {idx}: Beneficiary Name is required for Transfer Out")
        
        # Validate amount based on currency
        payment_currency = row.get("Payment Currency", "NGN")
        
        if payment_currency == "NGN":
            if not row.get("Amount Paid (NGN)"):
                row_errors.append(f"Row {idx}: Amount Paid (NGN) is required for NGN currency")
            elif flt(row.get("Amount Paid (NGN)")) <= 0:
                row_errors.append(f"Row {idx}: Amount Paid must be greater than zero")
        else:
            if not row.get("Amount Paid (Foreign Currency)"):
                row_errors.append(f"Row {idx}: Amount Paid (Foreign Currency) is required for non-NGN currency")
            elif flt(row.get("Amount Paid (Foreign Currency)")) <= 0:
                row_errors.append(f"Row {idx}: Amount Paid must be greater than zero")
            if not row.get("Exchange Rate") or flt(row.get("Exchange Rate")) <= 0:
                row_errors.append(f"Row {idx}: Valid Exchange Rate is required for foreign currency")
        
        # Validate WHT fields if WHT is enabled
        if row.get("Deduct WHT") in ["1", "Yes", "yes", "TRUE", "true", 1, True]:
            if not row.get("WHT Rate (%)"):
                row_errors.append(f"Row {idx}: WHT Rate is required when WHT is enabled")
            if not row.get("WHT Account"):
                row_errors.append(f"Row {idx}: WHT Account is required when WHT is enabled")
        
        # Validate nature of expense if customer is specified
        if row.get("Customer ID"):
            if row.get("Nature of Expense") != "For Customer":
                row_errors.append(f"Row {idx}: Nature of Expense must be 'For Customer' when Customer ID is specified")
            if not frappe.db.exists("Customer", row.get("Customer ID")):
                row_errors.append(f"Row {idx}: Customer '{row.get('Customer ID')}' does not exist")
        
        if row_errors:
            errors.extend(row_errors)
        else:
            validated_data.append(row)
    
    return {
        "success": len(errors) == 0,
        "errors": errors,
        "validated_count": len(validated_data),
        "error_count": len(errors)
    }


@frappe.whitelist()
def import_payments(data):
    """Import validated payments data"""
    
    frappe.flags.ignore_permissions = False
    imported = []
    failed = []
    
    # Parse data if it's a string
    if isinstance(data, str):
        data = json.loads(data)
    
    for idx, row in enumerate(data, start=1):
        try:
            # Create new Payment document
            payment = frappe.new_doc("Payments")
            
            # Set basic fields
            payment.transaction_date = getdate(row.get("Transaction Date"))
            payment.trans_type = row.get("Transaction Type")
            payment.company = row.get("Company")
            payment.payment_status = row.get("Payment Status") or "Draft"
            
            # Set beneficiary information
            if row.get("Supplier ID"):
                payment.payee_id = row.get("Supplier ID")
            if row.get("Beneficiary Name"):
                payment.payee_name = row.get("Beneficiary Name")
            if row.get("Customer ID"):
                payment.customer_id = row.get("Customer ID")
            
            # Set transaction options (convert to boolean)
            payment.create_accounting_entries = 1 if row.get("Create Accounting Entries") in ["1", "Yes", "yes", "TRUE", "true", 1, True] else 0
            payment.deduct_wht = 1 if row.get("Deduct WHT") in ["1", "Yes", "yes", "TRUE", "true", 1, True] else 0
            payment.amortize = 1 if row.get("Amortize Expense") in ["1", "Yes", "yes", "TRUE", "true", 1, True] else 0
            payment.is_multi_line = 1 if row.get("Multiple Line Items") in ["1", "Yes", "yes", "TRUE", "true", 1, True] else 0
            payment.is_shared_cost = 1 if row.get("Shared Cost Allocation") in ["1", "Yes", "yes", "TRUE", "true", 1, True] else 0
            payment.is_related_coy_trans = 1 if row.get("Inter-Company Transaction") in ["1", "Yes", "yes", "TRUE", "true", 1, True] else 0
            
            # Set accounting dimensions
            if row.get("Branch"):
                payment.branch = row.get("Branch")
            if row.get("Nature of Expense"):
                payment.nature_of_expense = row.get("Nature of Expense")
            if row.get("Cost Center"):
                payment.cost_center = row.get("Cost Center")
            if row.get("Department"):
                payment.department = row.get("Department")
            if row.get("Project"):
                payment.project = row.get("Project")
            
            # Set currency and exchange
            payment.payment_currency = row.get("Payment Currency")
            payment.exchange_rate = flt(row.get("Exchange Rate", 1))
            
            # Set amount
            if row.get("Payment Currency") == "NGN":
                payment.amount_paid = flt(row.get("Amount Paid (NGN)"))
            else:
                payment.amount_paid_in_fc = flt(row.get("Amount Paid (Foreign Currency)"))
            
            # Set payment details
            payment.mode_of_payment = row.get("Mode of Payment")
            payment.reference_no = row.get("Cheque/Reference No")
            if row.get("Account To Debit"):
                payment.account_to_debit = row.get("Account To Debit")
            payment.transaction_purposes = row.get("Transaction Purpose")
            
            # Set WHT details
            if payment.deduct_wht:
                payment.whtax_rate = flt(row.get("WHT Rate (%)"))
                payment.wht_account = row.get("WHT Account")
            
            # Set banking details
            payment.remittance_bank = row.get("Bank Account")
            payment.cashflow_type = row.get("Cash Flow Classification")
            if row.get("Approval Document Reference"):
                payment.approval_doc = row.get("Approval Document Reference")
            
            # Set approval/signature fields
            if row.get("Issued By"):
                payment.issued_by = row.get("Issued By")
                payment.date = getdate(row.get("Issue Date")) if row.get("Issue Date") else nowdate()
            
            if row.get("Authorised By"):
                payment.authorised_by = row.get("Authorised By")
                if row.get("Authorization Date"):
                    payment.auth_date = getdate(row.get("Authorization Date"))
            
            if row.get("Approved By"):
                payment.approved_by = row.get("Approved By")
                if row.get("Approval Date"):
                    payment.app_date = getdate(row.get("Approval Date"))
            
            # Insert the payment
            payment.insert()
            
            imported.append({
                "row": idx,
                "name": payment.name,
                "status": "Success"
            })
            
        except Exception as e:
            failed.append({
                "row": idx,
                "error": str(e),
                "data": row
            })
            frappe.log_error(f"Payment Import Error - Row {idx}", frappe.get_traceback())
    
    frappe.db.commit()
    
    return {
        "success": len(failed) == 0,
        "imported_count": len(imported),
        "failed_count": len(failed),
        "imported": imported,
        "failed": failed
    }