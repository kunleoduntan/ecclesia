# your_app/api/migration.py

import frappe
import openpyxl
from frappe.utils import cstr

@frappe.whitelist()
def create_rules_from_excel(file_path):
    """Create auto-coding rules from the provided Excel data"""
    
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    
    # Dictionary to store account to keywords mapping
    account_keywords = {}
    
    for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
        account = cstr(row[0]).strip()
        description = cstr(row[1]).strip() if row[1] else ""
        
        if not account or not description:
            continue
        
        # Extract keywords from description
        keywords = extract_keywords(description)
        
        if account not in account_keywords:
            account_keywords[account] = set()
        
        account_keywords[account].update(keywords)
    
    # Create rules
    for account, keywords in account_keywords.items():
        if not keywords:
            continue
        
        # Check if rule already exists
        existing = frappe.db.exists("Auto Coding Rule", {"account": account})
        
        if existing:
            # Update existing rule
            rule = frappe.get_doc("Auto Coding Rule", existing[0])
            existing_keywords = set(rule.keywords.split(", "))
            existing_keywords.update(keywords)
            rule.keywords = ", ".join(sorted(existing_keywords))
            rule.save()
        else:
            # Create new rule
            rule = frappe.get_doc({
                "doctype": "Auto Coding Rule",
                "rule_name": f"Rule for {account}",
                "keywords": ", ".join(sorted(keywords)),
                "account": account,
                "company": "Your Company Name",  # Update as needed
                "enabled": 1
            })
            rule.insert()
    
    frappe.db.commit()
    return f"Created/Updated {len(account_keywords)} rules"


def extract_keywords(text):
    """Extract meaningful keywords from transaction description"""
    
    # Common words to ignore
    stop_words = {
        "payment", "for", "being", "of", "to", "the", "and", "from", "with",
        "account", "details", "bank", "name", "number", "beneficiary", "note",
        "paid", "via", "card", "transfer", "refund", "cost", "total", "amount"
    }
    
    # Split and clean
    words = text.lower().split()
    
    # Filter words
    keywords = []
    for word in words:
        word = word.strip(".,!?;:()[]{}'\"")
        if len(word) > 2 and word not in stop_words:
            keywords.append(word)
    
    # Also capture common phrases
    phrases = [
        "pure water", "egg collection", "embryo transfer", "caution fee",
        "airport pickup", "monthly allowance", "office consumables",
        "vehicle fueling", "directors expenses", "medical consumables"
    ]
    
    for phrase in phrases:
        if phrase in text.lower():
            keywords.append(phrase.replace(" ", "_"))
    
    return keywords