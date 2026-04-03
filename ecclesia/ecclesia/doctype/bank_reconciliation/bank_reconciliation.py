# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, add_days, get_datetime
from datetime import datetime, timedelta
import json
import re
from difflib import SequenceMatcher


class BankReconciliation(Document):
    """Bank Reconciliation Document Class"""
    
    def validate(self):
        """Called on document save - validation"""
        # Call the validation method
        self.validate_bank_reconciliation()
        
        # Calculate totals
        self.calculate_all_totals()
        
        # Calculate balance
        self.calculate_final_balance()
    
    def validate_bank_reconciliation(self):
        """Custom validation for bank reconciliation"""
        # Ensure dates are valid
        if self.from_date and self.to_date:
            if getdate(self.from_date) > getdate(self.to_date):
                frappe.throw(_("From Date cannot be greater than To Date"))
        
        # Ensure required fields are set
        if not self.bank_gl:
            frappe.throw(_("Bank Account (GL) is required"))
        
        if not self.company:
            frappe.throw(_("Company is required"))
        
        if not self.bank_account:
            frappe.throw(_("Bank Account is required"))
        
        # Validate statement ending balance
        if not self.statement_ending_balance:
            frappe.throw(_("Statement Ending Balance is required"))
        
        # Validate cashbook ending balance
        if not self.cashbook_ending_balance:
            frappe.throw(_("Cashbook Ending Balance is required"))
    
    def calculate_all_totals(self):
        """Calculate all totals"""
        self.total_debit = sum(flt(row.debit_amount) for row in self.bank_account_entry)
        self.total_credit = sum(flt(row.credit_amount) for row in self.bank_account_entry)
        self.total_unpresented_cheque = sum(flt(row.credit_amount) for row in self.unpresented_cheques)
        self.total_uncredited_cheque = sum(flt(row.debit_amount) for row in self.uncredited_cheques)
        self.total_direct_withdrawal = sum(flt(row.debit_amount) for row in self.direct_withdrawal)
        self.total_direct_lodgment = sum(flt(row.credit_amount) for row in self.direct_lodgment)
    
    def calculate_final_balance(self):
        """Calculate final reconciliation balance"""
        balance_per_cb = (
            flt(self.statement_ending_balance) +
            flt(self.total_unpresented_cheque) -
            flt(self.total_uncredited_cheque) +
            flt(self.total_direct_withdrawal) -
            flt(self.total_direct_lodgment)
        )
        
        self.balance_per_cash_book = balance_per_cb
        self.balance_diff = flt(self.cashbook_ending_balance) - balance_per_cb
        
        # Set status
        if abs(self.balance_diff) < 0.01:  # Allow for rounding
            self.status = "Reconciled"
        else:
            self.status = "Not Reconciled"


# ============ FILE UPLOAD & IMPORT ============

@frappe.whitelist()
def preview_statement_file(file_url, docname):
    """
    Preview uploaded CSV/Excel file
    Returns columns and preview rows
    """
    try:
        # Get file document
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()
        
        # Determine file type and read accordingly
        if file_path.endswith(('.xlsx', '.xls')):
            import openpyxl
            
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            
            # Get headers
            headers = [str(cell.value) if cell.value is not None else '' for cell in ws[1]]
            
            # Get preview rows (first 10 rows)
            preview_rows = []
            for row in ws.iter_rows(min_row=2, max_row=11, values_only=True):
                preview_rows.append([str(cell) if cell is not None else '' for cell in row])
            
            # Get total row count
            total_rows = ws.max_row - 1  # Exclude header
            
        else:  # CSV
            import csv
            
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader)
                
                preview_rows = []
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    preview_rows.append(row)
                
                # Count total rows
                f.seek(0)
                total_rows = sum(1 for _ in reader) - 1  # Exclude header
        
        return {
            "columns": headers,
            "preview_rows": preview_rows,
            "total_rows": total_rows
        }
        
    except Exception as e:
        frappe.log_error(f"Error previewing file: {str(e)}", "Bank Reconciliation File Preview")
        frappe.throw(_("Error reading file: {0}").format(str(e)))


@frappe.whitelist()
def import_bank_statement_with_mapping(docname, file_url, date_column, party_column, 
                                      debit_column, credit_column, header_row=1, 
                                      clear_existing=0, skip_duplicates=1):
    """
    Import bank statement with column mapping
    Supports both CSV and Excel files
    """
    try:
        doc = frappe.get_doc("Bank Reconciliation", docname)
        
        # Get file
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()
        
        # Clear existing if requested
        if int(clear_existing):
            doc.bank_statement = []
        
        # Track existing vouchers if skipping duplicates
        existing_vouchers = set()
        if int(skip_duplicates):
            for stmt in doc.bank_statement:
                if stmt.voucher_no:
                    existing_vouchers.add(stmt.voucher_no)
        
        imported = 0
        skipped = 0
        errors = []
        
        # Read file based on type
        if file_path.endswith(('.xlsx', '.xls')):
            import openpyxl
            
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            
            # Get column indices
            headers = [cell.value for cell in ws[int(header_row)]]
            col_map = {
                'date': headers.index(date_column) if date_column in headers else None,
                'party': headers.index(party_column) if party_column in headers else None,
                'debit': headers.index(debit_column) if debit_column in headers else None,
                'credit': headers.index(credit_column) if credit_column in headers else None
            }
            
            # Process rows
            for row_idx, row in enumerate(ws.iter_rows(min_row=int(header_row)+1, values_only=True), 1):
                try:
                    # Extract values
                    date_val = row[col_map['date']] if col_map['date'] is not None else None
                    party_val = row[col_map['party']] if col_map['party'] is not None else ''
                    debit_val = row[col_map['debit']] if col_map['debit'] is not None else 0
                    credit_val = row[col_map['credit']] if col_map['credit'] is not None else 0
                    
                    # Parse date
                    if isinstance(date_val, datetime):
                        posting_date = date_val.date()
                    elif date_val:
                        posting_date = getdate(date_val)
                    else:
                        errors.append(f"Row {row_idx}: Missing date")
                        continue
                    
                    # Generate voucher_no
                    voucher_no = f"{posting_date}_{party_val}_{debit_val or credit_val}"[:140]
                    
                    # Skip if duplicate
                    if int(skip_duplicates) and voucher_no in existing_vouchers:
                        skipped += 1
                        continue
                    
                    # Add to child table
                    doc.append("bank_statement", {
                        "posting_date": posting_date,
                        "party": str(party_val)[:140] if party_val else "",
                        "debit_amount": flt(debit_val) if debit_val else 0.0,
                        "credit_amount": flt(credit_val) if credit_val else 0.0,
                        "account_currency": doc.account_currency,
                        "voucher_no": voucher_no,
                        "rec": 0
                    })
                    
                    existing_vouchers.add(voucher_no)
                    imported += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_idx}: {str(e)}")
                    
        else:  # CSV
            import csv
            
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row_idx, row in enumerate(reader, 1):
                    try:
                        # Extract values
                        date_val = row.get(date_column)
                        party_val = row.get(party_column, '')
                        debit_val = row.get(debit_column, 0)
                        credit_val = row.get(credit_column, 0)
                        
                        # Parse date
                        if date_val:
                            posting_date = getdate(date_val)
                        else:
                            errors.append(f"Row {row_idx}: Missing date")
                            continue
                        
                        # Generate voucher_no
                        voucher_no = f"{posting_date}_{party_val}_{debit_val or credit_val}"[:140]
                        
                        # Skip if duplicate
                        if int(skip_duplicates) and voucher_no in existing_vouchers:
                            skipped += 1
                            continue
                        
                        # Add to child table
                        doc.append("bank_statement", {
                            "posting_date": posting_date,
                            "party": str(party_val)[:140] if party_val else "",
                            "debit_amount": flt(debit_val) if debit_val else 0.0,
                            "credit_amount": flt(credit_val) if credit_val else 0.0,
                            "account_currency": doc.account_currency,
                            "voucher_no": voucher_no,
                            "rec": 0
                        })
                        
                        existing_vouchers.add(voucher_no)
                        imported += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_idx}: {str(e)}")
        
        # Save document
        if imported > 0:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
        
        # Log errors if any
        if errors:
            error_log = "\n".join(errors[:50])  # First 50 errors
            frappe.log_error(error_log, f"Bank Statement Import Errors - {docname}")
        
        return {
            "count": imported,
            "skipped": skipped,
            "errors": len(errors),
            "status": "success"
        }
        
    except Exception as e:
        frappe.log_error(f"Import failed: {str(e)}", "Bank Statement Import")
        frappe.throw(_("Import failed: {0}").format(str(e)))


# ============ ADVANCED MATCHING ENGINE ============

@frappe.whitelist()
def advanced_auto_match(docname, match_tolerance=1.0, date_range=5, cross_match=1,
                       fuzzy_party=1, min_confidence=60, auto_match_high=1):
    """
    Advanced intelligent matching algorithm
    Uses multiple matching strategies with confidence scoring
    """
    try:
        doc = frappe.get_doc("Bank Reconciliation", docname)
        
        entries = doc.bank_account_entry
        statements = doc.bank_statement
        
        if not entries or not statements:
            frappe.throw(_("No entries or statements to match"))
        
        match_tolerance = flt(match_tolerance)
        date_range = int(date_range)
        min_confidence = flt(min_confidence) / 100  # Convert to 0-1
        
        results = {
            "auto_matched": 0,
            "suggested": 0,
            "unmatched": 0,
            "review_items": [],
            "total": len(entries)
        }
        
        matched_statements = set()
        
        # Process each entry
        for entry_idx, entry in enumerate(entries):
            # Skip already matched
            if entry.rec == 1:
                continue
            
            best_match = None
            best_score = 0
            
            # Find best matching statement
            for stmt_idx, stmt in enumerate(statements):
                # Skip already matched
                if stmt_idx in matched_statements or stmt.rec == 1:
                    continue
                
                # Calculate match score
                score = calculate_match_score(
                    entry, stmt, match_tolerance, date_range,
                    int(cross_match), int(fuzzy_party)
                )
                
                if score > best_score:
                    best_score = score
                    best_match = (stmt_idx, stmt, score)
            
            # Process best match
            if best_match and best_score >= min_confidence:
                stmt_idx, stmt, confidence = best_match
                
                # Auto-match if high confidence and auto_match_high enabled
                if confidence >= 0.9 and int(auto_match_high):
                    entry.rec = 1
                    stmt.rec = 1
                    entry.match_confidence = confidence * 100
                    entry.match_method = "Auto - High Confidence"
                    stmt.match_confidence = confidence * 100
                    matched_statements.add(stmt_idx)
                    results["auto_matched"] += 1
                    
                # Add to review list if medium confidence
                elif confidence >= min_confidence:
                    match_type = determine_match_type(entry, stmt, int(cross_match))
                    
                    results["review_items"].append({
                        "entry_idx": entry.idx,
                        "statement_idx": stmt.idx,
                        "entry": {
                            "party": entry.party or "",
                            "amount": flt(entry.debit_amount or entry.credit_amount),
                            "date": str(entry.posting_date),
                            "voucher": entry.voucher_no
                        },
                        "statement": {
                            "party": stmt.party or "",
                            "amount": flt(stmt.debit_amount or stmt.credit_amount),
                            "date": str(stmt.posting_date),
                            "voucher": stmt.voucher_no
                        },
                        "confidence": confidence,
                        "match_type": match_type
                    })
                    results["suggested"] += 1
                    
            else:
                results["unmatched"] += 1
        
        # Calculate percentages
        total = results["total"]
        results["auto_matched_pct"] = round((results["auto_matched"] / total * 100) if total > 0 else 0, 1)
        results["suggested_pct"] = round((results["suggested"] / total * 100) if total > 0 else 0, 1)
        results["unmatched_pct"] = round((results["unmatched"] / total * 100) if total > 0 else 0, 1)
        
        # Save document
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Matching error: {str(e)}", "Advanced Auto Match")
        frappe.throw(_("Matching failed: {0}").format(str(e)))


def calculate_match_score(entry, stmt, tolerance, date_range, cross_match, fuzzy_party):
    """
    Calculate comprehensive match score (0.0 to 1.0)
    Uses weighted scoring across multiple factors
    """
    score = 0.0
    
    # 1. AMOUNT MATCHING (40% weight)
    entry_debit = flt(entry.debit_amount)
    entry_credit = flt(entry.credit_amount)
    stmt_debit = flt(stmt.debit_amount)
    stmt_credit = flt(stmt.credit_amount)
    
    # Direct amount match (same side)
    if entry_debit > 0 and stmt_debit > 0:
        diff = abs(entry_debit - stmt_debit)
        if diff <= tolerance:
            score += 0.4
        elif diff / max(entry_debit, stmt_debit) < 0.05:  # 5% variance
            score += 0.35
        elif diff / max(entry_debit, stmt_debit) < 0.10:  # 10% variance
            score += 0.25
            
    elif entry_credit > 0 and stmt_credit > 0:
        diff = abs(entry_credit - stmt_credit)
        if diff <= tolerance:
            score += 0.4
        elif diff / max(entry_credit, stmt_credit) < 0.05:
            score += 0.35
        elif diff / max(entry_credit, stmt_credit) < 0.10:
            score += 0.25
    
    # Cross-match (debit ↔ credit)
    if cross_match:
        if entry_debit > 0 and stmt_credit > 0:
            diff = abs(entry_debit - stmt_credit)
            if diff <= tolerance:
                score += 0.35  # Slightly lower weight for cross-match
            elif diff / max(entry_debit, stmt_credit) < 0.05:
                score += 0.30
                
        elif entry_credit > 0 and stmt_debit > 0:
            diff = abs(entry_credit - stmt_debit)
            if diff <= tolerance:
                score += 0.35
            elif diff / max(entry_credit, stmt_debit) < 0.05:
                score += 0.30
    
    # 2. DATE MATCHING (30% weight)
    try:
        entry_date = getdate(entry.posting_date)
        stmt_date = getdate(stmt.posting_date)
        date_diff = abs((entry_date - stmt_date).days)
        
        if date_diff == 0:
            score += 0.30  # Same day
        elif date_diff == 1:
            score += 0.25  # 1 day difference
        elif date_diff <= date_range:
            score += 0.30 * (1 - date_diff / date_range)  # Proportional
    except:
        pass
    
    # 3. PARTY NAME MATCHING (25% weight)
    if fuzzy_party:
        party_score = fuzzy_party_match(entry.party or "", stmt.party or "")
        score += 0.25 * party_score
    else:
        # Exact match only
        if (entry.party or "").lower().strip() == (stmt.party or "").lower().strip():
            score += 0.25
    
    # 4. VOUCHER/CHEQUE NUMBER MATCHING (5% weight - bonus)
    if entry.voucher_no and stmt.voucher_no:
        if entry.voucher_no.lower() == stmt.voucher_no.lower():
            score += 0.05
    
    if entry.cheque_no and stmt.cheque_no:
        if entry.cheque_no.lower() == stmt.cheque_no.lower():
            score += 0.05
    
    return min(score, 1.0)  # Cap at 1.0


def fuzzy_party_match(party1, party2):
    """
    Intelligent fuzzy matching for party names
    Returns score 0.0 to 1.0
    """
    if not party1 or not party2:
        return 0.0
    
    # Normalize
    p1 = normalize_party_name(party1)
    p2 = normalize_party_name(party2)
    
    # Exact match
    if p1 == p2:
        return 1.0
    
    # Use SequenceMatcher for similarity
    similarity = SequenceMatcher(None, p1, p2).ratio()
    
    # Check for substring match (boost score)
    if len(p1) >= 3 and len(p2) >= 3:
        if p1 in p2 or p2 in p1:
            similarity = max(similarity, 0.85)
    
    # Check for common words
    words1 = set(p1.split())
    words2 = set(p2.split())
    
    # Filter out common words
    common_stopwords = {'ltd', 'limited', 'pvt', 'private', 'inc', 'corp', 'the', 'and', '&'}
    words1 = {w for w in words1 if w not in common_stopwords and len(w) >= 3}
    words2 = {w for w in words2 if w not in common_stopwords and len(w) >= 3}
    
    if words1 and words2:
        common_words = words1.intersection(words2)
        word_similarity = len(common_words) / max(len(words1), len(words2))
        similarity = max(similarity, word_similarity)
    
    return similarity


def normalize_party_name(party):
    """Normalize party name for comparison"""
    if not party:
        return ""
    
    # Convert to lowercase
    name = party.lower().strip()
    
    # Remove special characters
    name = re.sub(r'[^\w\s]', ' ', name)
    
    # Normalize spaces
    name = ' '.join(name.split())
    
    return name


def determine_match_type(entry, stmt, cross_match):
    """Determine the type of match found"""
    entry_debit = flt(entry.debit_amount)
    entry_credit = flt(entry.credit_amount)
    stmt_debit = flt(stmt.debit_amount)
    stmt_credit = flt(stmt.credit_amount)
    
    if entry_debit > 0 and stmt_debit > 0:
        return "Direct Debit Match"
    elif entry_credit > 0 and stmt_credit > 0:
        return "Direct Credit Match"
    elif cross_match and entry_debit > 0 and stmt_credit > 0:
        return "Cross Match (Entry Debit ↔ Statement Credit)"
    elif cross_match and entry_credit > 0 and stmt_debit > 0:
        return "Cross Match (Entry Credit ↔ Statement Debit)"
    else:
        return "Amount Match"


@frappe.whitelist()
def apply_suggested_matches(docname, selected_indices):
    """
    Apply selected suggested matches
    """
    try:
        doc = frappe.get_doc("Bank Reconciliation", docname)
        
        if isinstance(selected_indices, str):
            selected_indices = json.loads(selected_indices)
        
        applied = 0
        
        for idx in selected_indices:
            idx = int(idx)
            applied += 1
        
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {"applied": applied}
        
    except Exception as e:
        frappe.log_error(f"Apply matches error: {str(e)}", "Apply Suggested Matches")
        frappe.throw(_("Failed to apply matches: {0}").format(str(e)))


@frappe.whitelist()
def save_manual_matches(docname, matches):
    """
    Save manually created matches
    """
    try:
        doc = frappe.get_doc("Bank Reconciliation", docname)
        
        if isinstance(matches, str):
            matches = json.loads(matches)
        
        for match in matches:
            entry_idx = match.get("entry_idx")
            stmt_idx = match.get("statement_idx")
            
            # Find and mark as reconciled
            for entry in doc.bank_account_entry:
                if entry.idx == entry_idx:
                    entry.rec = 1
                    entry.match_method = "Manual Match"
                    break
            
            for stmt in doc.bank_statement:
                if stmt.idx == stmt_idx:
                    stmt.rec = 1
                    break
        
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {"saved": len(matches)}
        
    except Exception as e:
        frappe.log_error(f"Save manual matches error: {str(e)}", "Save Manual Matches")
        frappe.throw(_("Failed to save manual matches: {0}").format(str(e)))


# ============ GET BANK ENTRIES - GL ENTRY ONLY ============

@frappe.whitelist()
def get_bank_reco_entries(docname):
    """
    Fetch bank reconciliation entries from GL Entry ONLY
    No direct retrieval from Receipts/Payments
    """
    try:
        doc = frappe.get_doc("Bank Reconciliation", docname)
        
        if not doc.from_date or not doc.to_date or not doc.bank_gl:
            frappe.throw(_("Please set From Date, To Date, and Bank Account"))
        
        start_date = getdate(doc.from_date)
        end_date = getdate(doc.to_date)
        bank_gl = doc.bank_gl
        company = doc.company
        
        # Query GL entries ONLY - removed any reference to Receipts/Payments
        query = """
            SELECT
                gle.posting_date,
                gle.account,
                gle.debit AS debit_amount,
                gle.credit AS credit_amount,
                gle.account_currency,
                gle.against,
                gle.voucher_no,
                gle.voucher_type,
                gle.remarks,
                gle.party_type,
                gle.party
            FROM `tabGL Entry` gle
            WHERE gle.posting_date BETWEEN %s AND %s
              AND gle.account = %s
              AND gle.company = %s
              AND gle.is_cancelled = 0
            ORDER BY gle.posting_date, gle.voucher_no
        """
        
        entries = frappe.db.sql(query, (start_date, end_date, bank_gl, company), as_dict=True)
        
        if not entries:
            frappe.msgprint(_("No GL entries found for the specified criteria"))
            return {"status": "ok", "count": 0}
        
        # Track existing entries to avoid duplicates
        existing = set()
        for row in doc.bank_account_entry:
            key = (
                str(row.voucher_no or ''),
                flt(row.debit_amount or 0),
                flt(row.credit_amount or 0),
                str(row.posting_date or '')
            )
            existing.add(key)
        
        appended = 0
        
        for entry in entries:
            # Get party information from GL Entry
            party = entry.party or entry.against or ""
            
            # Get cheque number from source document
            cheque_no = get_cheque_no_from_voucher(entry.voucher_type, entry.voucher_no)
            
            # Create unique key
            key = (
                str(entry.voucher_no or ''),
                flt(entry.debit_amount or 0),
                flt(entry.credit_amount or 0),
                str(entry.posting_date or '')
            )
            
            # Check if exists
            if key not in existing:
                doc.append("bank_account_entry", {
                    "posting_date": entry.posting_date,
                    "party": (party or "")[:140],
                    "voucher_no": entry.voucher_no,
                    "debit_amount": flt(entry.debit_amount),
                    "credit_amount": flt(entry.credit_amount),
                    "account_currency": entry.account_currency,
                    "cheque_no": cheque_no,
                    "remarks": entry.remarks,
                    "rec": 0
                })
                
                existing.add(key)
                appended += 1
        
        # Calculate cashbook balance from GL Entry
        calculate_cashbook_balance(doc, bank_gl, start_date, end_date, company)
        
        # Save
        if appended > 0:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
        
        return {"status": "success", "count": appended}
        
    except Exception as e:
        frappe.log_error(f"Error in get_bank_reco_entries: {str(e)}", "Get Bank Entries")
        frappe.throw(_("Error fetching bank entries: {0}").format(str(e)))


def get_cheque_no_from_voucher(voucher_type, voucher_no):
    """Get cheque number from various voucher types"""
    try:
        if voucher_type == "Payment Entry":
            return frappe.db.get_value("Payment Entry", voucher_no, "reference_no")
            
        elif voucher_type == "Journal Entry":
            return frappe.db.get_value("Journal Entry", voucher_no, "cheque_no")
        
        elif voucher_type == "Payments":
            return frappe.db.get_value("Payments", voucher_no, "reference_no")
        
        elif voucher_type == "Receipts":
            return frappe.db.get_value("Receipts", voucher_no, "reference_no")
            
    except:
        pass
    
    return None


def calculate_cashbook_balance(doc, bank_gl, start_date, end_date, company):
    """Calculate cashbook ending balance from GL Entry"""
    try:
        result = frappe.db.sql("""
            SELECT SUM(gle.debit - gle.credit) AS balance
            FROM `tabGL Entry` gle
            WHERE gle.account = %s
              AND gle.posting_date <= %s
              AND gle.company = %s
              AND gle.is_cancelled = 0
        """, (bank_gl, end_date, company), as_dict=1)
        
        balance = flt(result[0].get("balance", 0)) if result else 0
        doc.cashbook_ending_balance = balance
        
    except Exception as e:
        frappe.log_error(f"Error calculating balance: {str(e)}", "Calculate Cashbook Balance")


@frappe.whitelist()
def create_payments_and_receipts_transactions(docname):
    """
    Create Payments (not Payment Entry) for Direct Withdrawals
    Create Receipts for Direct Lodgments
    WITH DUPLICATE PREVENTION
    """
    try:
        doc = frappe.get_doc("Bank Reconciliation", docname)
        
        created_payments = 0
        created_receipts = 0
        skipped_payments = 0
        skipped_receipts = 0
        errors = []
        
        # Get current user's full name
        try:
            current_user_fullname = frappe.get_value("User", frappe.session.user, "full_name")
        except:
            current_user_fullname = frappe.session.user
        
        # ========== CREATE PAYMENTS FOR DIRECT WITHDRAWALS ==========
        for dw in doc.direct_withdrawal:
            if flt(dw.debit_amount) <= 0:
                continue
            
            try:
                # CHECK FOR DUPLICATE PAYMENT
                duplicate_check = check_payment_exists(
                    transaction_date=dw.posting_date,
                    amount=flt(dw.debit_amount),
                    reference_no=dw.cheque_no or dw.voucher_no,
                    payee_name=dw.party,
                    company=doc.company
                )
                
                if duplicate_check:
                    skipped_payments += 1
                    frappe.msgprint(
                        _(f"Payment already exists: {duplicate_check} for {dw.party} - Skipped"),
                        indicator='orange',
                        alert=True
                    )
                    continue
                
                # CREATE NEW PAYMENT
                payment = frappe.new_doc('Payments')
                payment.transaction_date = dw.posting_date
                payment.payee_name = (dw.party or "Bank Charges").title()
                
                # Account to debit - use bank GL
                payment.account_to_debit = doc.bank_gl
                
                payment.trans_type = "Expense Payment"
                payment.payment_currency = doc.account_currency
                
                # Get cost center from company
                try:
                    cost_center = frappe.get_value("Company", doc.company, "cost_center")
                    payment.cost_center = cost_center
                except:
                    pass
                
                payment.transaction_purposes = (dw.remarks or "Direct Withdrawal from Bank Reconciliation").title()
                payment.mode_of_payment = "Wire Transfer"
                payment.remittance_bank = doc.bank_account
                payment.remittance_bank_gl = doc.bank_gl
                payment.amount_paid = flt(dw.debit_amount)
                
                # Exchange rate handling
                if doc.account_currency == "NGN":
                    payment.exchange_rate = 1
                
                payment.nature_of_expense = "Internal"
                payment.create_accounting_entries = 1
                
                # Reference numbers
                payment.approval_doc = dw.voucher_no or ""
                payment.reference_no = dw.cheque_no or dw.voucher_no or f"BR-{doc.name}-DW-{dw.idx}"
                
                # User and dates
                payment.issued_by = frappe.session.user
                payment.date = frappe.utils.today()
                payment.cashflow_type = "Payment of Operation"
                payment.auth_date = frappe.utils.today()
                payment.app_date = frappe.utils.today()
                
                # Company
                payment.company = doc.company
                
                # Insert the payment (don't submit - let user review)
                payment.insert(ignore_permissions=True)
                
                frappe.msgprint(
                    _(f"✓ Created Payment: {payment.name} for {dw.party}"),
                    indicator='green',
                    alert=True
                )
                created_payments += 1
                
            except Exception as e:
                error_msg = f"DW Row {dw.idx} ({dw.party}): {str(e)}"
                errors.append(error_msg)
                frappe.log_error(error_msg, "Create Payment Error")
                frappe.msgprint(
                    _(f"✗ Error creating payment for {dw.party}: {str(e)}"),
                    indicator='red',
                    alert=True
                )
        
        # ========== CREATE RECEIPTS FOR DIRECT LODGMENTS ==========
        for dl in doc.direct_lodgment:
            if flt(dl.credit_amount) <= 0:
                continue
            
            try:
                # CHECK FOR DUPLICATE RECEIPT
                duplicate_check = check_receipt_exists(
                    transaction_date=dl.posting_date,
                    amount=flt(dl.credit_amount),
                    reference_no=dl.cheque_no or dl.voucher_no,
                    customer_name=dl.party,
                    company=doc.company
                )
                
                if duplicate_check:
                    skipped_receipts += 1
                    frappe.msgprint(
                        _(f"Receipt already exists: {duplicate_check} for {dl.party} - Skipped"),
                        indicator='orange',
                        alert=True
                    )
                    continue
                
                # CREATE NEW RECEIPT
                receipt = frappe.new_doc("Receipts")
                receipt.transaction_date = dl.posting_date
                receipt.customer_type = 'Receive from Registered'
                
                # Get cost center
                try:
                    cost_center = frappe.get_value("Company", doc.company, "cost_center")
                    receipt.cost_center = cost_center
                except:
                    pass
                
                # Customer info
                receipt.customer_id = dl.party or ""
                receipt.customer_name = (dl.party or "Direct Lodgment").title()
                
                receipt.create_accounting_entries = 1
                receipt.transaction_purposes = (dl.remarks or "Direct Lodgment from Bank Reconciliation").title()
                receipt.receipt_currency = doc.account_currency
                receipt.amount_paid = flt(dl.credit_amount)
                receipt.mode_of_payment = "Wire Transfer"
                
                # Reference numbers
                receipt.reference_no = dl.cheque_no or dl.voucher_no or f"BR-{doc.name}-DL-{dl.idx}"
                receipt.referenced_document_no = doc.name
                
                receipt.remittance_bank = doc.bank_account
                receipt.remittance_bank_gl = doc.bank_gl
                
                receipt.approval_doc = dl.voucher_no or ""
                receipt.issued_by = frappe.session.user
                receipt.name_of_issued_by = current_user_fullname
                receipt.date = frappe.utils.today()
                
                # Company
                receipt.company = doc.company
                
                # Insert the receipt (don't submit - let user review)
                receipt.insert(ignore_permissions=True)
                
                frappe.msgprint(
                    _(f"✓ Created Receipt: {receipt.name} for {dl.party}"),
                    indicator='green',
                    alert=True
                )
                created_receipts += 1
                
            except Exception as e:
                error_msg = f"DL Row {dl.idx} ({dl.party}): {str(e)}"
                errors.append(error_msg)
                frappe.log_error(error_msg, "Create Receipt Error")
                frappe.msgprint(
                    _(f"✗ Error creating receipt for {dl.party}: {str(e)}"),
                    indicator='red',
                    alert=True
                )
        
        # Log all errors if any
        if errors:
            error_log = "\n".join(errors)
            frappe.log_error(error_log, f"Create Transactions Errors - {docname}")
        
        # Commit if successful
        if created_payments > 0 or created_receipts > 0:
            frappe.db.commit()
        
        # Show final summary
        summary_message = []
        if created_payments > 0:
            summary_message.append(f"✓ Created {created_payments} Payment(s)")
        if skipped_payments > 0:
            summary_message.append(f"⊘ Skipped {skipped_payments} duplicate Payment(s)")
        if created_receipts > 0:
            summary_message.append(f"✓ Created {created_receipts} Receipt(s)")
        if skipped_receipts > 0:
            summary_message.append(f"⊘ Skipped {skipped_receipts} duplicate Receipt(s)")
        if errors:
            summary_message.append(f"✗ {len(errors)} Error(s)")
        
        if summary_message:
            frappe.msgprint({
                'title': _('Transaction Creation Summary'),
                'message': '<br>'.join(summary_message),
                'indicator': 'green' if not errors else 'orange'
            })
        
        # Return summary
        result = {
            "payments": created_payments,
            "receipts": created_receipts,
            "skipped_payments": skipped_payments,
            "skipped_receipts": skipped_receipts,
            "errors": len(errors),
            "total_created": created_payments + created_receipts
        }
        
        if errors:
            result["error_details"] = errors
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Create transactions error: {str(e)}", "Create Transactions")
        frappe.throw(_("Failed to create transactions: {0}").format(str(e)))


# ============ DUPLICATE CHECKING FUNCTIONS ============

def check_payment_exists(transaction_date, amount, reference_no, payee_name, company):
    """
    Check if a Payment already exists with the same details
    Returns the payment name if exists, None otherwise
    """
    try:
        # Build filters for duplicate check
        filters = {
            "transaction_date": transaction_date,
            "amount_paid": amount,
            "company": company,
            "docstatus": ["!=", 2]  # Exclude cancelled documents
        }
        
        # Add reference number if available
        if reference_no:
            filters["reference_no"] = reference_no
        
        # Check if payment exists
        existing_payment = frappe.db.get_value(
            "Payments",
            filters,
            "name"
        )
        
        if existing_payment:
            return existing_payment
        
        # If no reference number, do additional check with payee name
        if not reference_no and payee_name:
            filters_alt = {
                "transaction_date": transaction_date,
                "amount_paid": amount,
                "payee_name": payee_name,
                "company": company,
                "docstatus": ["!=", 2]
            }
            
            existing_payment = frappe.db.get_value(
                "Payments",
                filters_alt,
                "name"
            )
            
            return existing_payment
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error checking payment duplicate: {str(e)}", "Payment Duplicate Check")
        return None


def check_receipt_exists(transaction_date, amount, reference_no, customer_name, company):
    """
    Check if a Receipt already exists with the same details
    Returns the receipt name if exists, None otherwise
    """
    try:
        # Build filters for duplicate check
        filters = {
            "transaction_date": transaction_date,
            "amount_paid": amount,
            "company": company,
            "docstatus": ["!=", 2]  # Exclude cancelled documents
        }
        
        # Add reference number if available
        if reference_no:
            filters["reference_no"] = reference_no
        
        # Check if receipt exists
        existing_receipt = frappe.db.get_value(
            "Receipts",
            filters,
            "name"
        )
        
        if existing_receipt:
            return existing_receipt
        
        # If no reference number, do additional check with customer name
        if not reference_no and customer_name:
            filters_alt = {
                "transaction_date": transaction_date,
                "amount_paid": amount,
                "customer_name": customer_name,
                "company": company,
                "docstatus": ["!=", 2]
            }
            
            existing_receipt = frappe.db.get_value(
                "Receipts",
                filters_alt,
                "name"
            )
            
            return existing_receipt
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error checking receipt duplicate: {str(e)}", "Receipt Duplicate Check")
        return None
        
        
# ============ SMART SUGGESTIONS ============

@frappe.whitelist()
def get_smart_suggestions(docname):
    """
    Generate smart suggestions for reconciliation
    """
    try:
        doc = frappe.get_doc("Bank Reconciliation", docname)
        suggestions = []
        
        # 1. Check for large unmatched amounts
        unmatched_entries = [e for e in doc.bank_account_entry if e.rec == 0]
        if unmatched_entries:
            large_amounts = [e for e in unmatched_entries 
                            if flt(e.debit_amount or e.credit_amount or 0) > 10000]
            
            if large_amounts:
                suggestions.append({
                    "type": "Critical",
                    "priority": "critical",
                    "title": f"{len(large_amounts)} Large Unmatched Transactions",
                    "description": "You have large value transactions that are not matched. These should be prioritized.",
                    "action": "highlight_large",
                    "action_label": "Show Transactions"
                })
        
        # 2. Check for old unmatched items
        from datetime import datetime
        old_date = add_days(nowdate(), -30)
        old_unmatched = [e for e in unmatched_entries 
                        if getdate(e.posting_date) < getdate(old_date)]
        
        if old_unmatched:
            suggestions.append({
                "type": "Warning",
                "priority": "warning",
                "title": f"{len(old_unmatched)} Old Unmatched Items",
                "description": "Some unmatched items are over 30 days old. Consider investigating these.",
                "action": None,
                "action_label": None
            })
        
        # 3. Check for potential duplicates
        seen = {}
        duplicates = []
        for entry in doc.bank_account_entry:
            key = f"{entry.posting_date}_{entry.party}_{flt(entry.debit_amount or entry.credit_amount or 0)}"
            if key in seen:
                duplicates.append(entry)
            seen[key] = entry
        
        if duplicates:
            suggestions.append({
                "type": "Warning",
                "priority": "warning",
                "title": "Potential Duplicates Detected",
                "description": f"Found {len(duplicates)} potential duplicate entries. Use the duplicate checker to review.",
                "action": "check_duplicates",
                "action_label": "Check Duplicates"
            })
        
        # 4. Check matching rate
        total = len(doc.bank_account_entry)
        matched = len([e for e in doc.bank_account_entry if e.rec == 1])
        
        if total > 0:
            match_rate = (matched / total) * 100
            
            if match_rate < 50:
                suggestions.append({
                    "type": "Critical",
                    "priority": "critical",
                    "title": "Low Match Rate",
                    "description": f"Only {match_rate:.1f}% of transactions are matched. Consider using auto-matching.",
                    "action": "run_matching",
                    "action_label": "Run Auto Match"
                })
            elif match_rate >= 90:
                suggestions.append({
                    "type": "Info",
                    "priority": "info",
                    "title": "Great Progress!",
                    "description": f"{match_rate:.1f}% matched! You're almost done.",
                    "action": None,
                    "action_label": None
                })
        
        # 5. Check balance difference
        if abs(flt(doc.balance_diff or 0)) > 0.01:
            suggestions.append({
                "type": "Critical",
                "priority": "critical",
                "title": "Balance Mismatch",
                "description": f"There's a difference of {frappe.utils.fmt_money(abs(flt(doc.balance_diff)), doc.account_currency)}. Ensure all reconciling items are captured.",
                "action": None,
                "action_label": None
            })
        
        return suggestions
        
    except Exception as e:
        frappe.log_error(f"Smart suggestions error: {str(e)}", "Smart Suggestions Error")
        return []


# ============ STANDALONE VALIDATION FUNCTION ============

@frappe.whitelist()
def validate_bank_reconciliation(docname):
    """
    Standalone function to validate bank reconciliation
    Can be called from external sources
    """
    try:
        doc = frappe.get_doc("Bank Reconciliation", docname)
        
        # Call the instance method
        doc.validate_bank_reconciliation()
        
        return {
            "status": "success",
            "message": "Bank reconciliation validated successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Validation error: {str(e)}", "Bank Reconciliation Validation")
        return {
            "status": "error",
            "message": str(e)
        }