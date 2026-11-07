# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt




import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today, add_days, cstr
import json
from datetime import datetime


from ecclesia.api import voucher_router as vr
from ecclesia.api import batch_excel_io as xio


_SHEET = "Bank Transactions"
_CHILD = "Transaction Entry"


def _trans_type_options():
    """The Select options actually defined on the child table."""
    df = frappe.get_meta(_CHILD).get_field("trans_type")
    return [o.strip() for o in (df.options or "").split("\n") if o.strip()] if df else []


def _columns():
    """Excel layout. Built at call time so Trans Type validates against the
    options your child table really has."""
    return [
        ("Date*",           "posting_date",         True,  "date",  {"width": 12, "example": "2026-11-02",
                                                                     "note": "Cannot be in the future."}),
        ("Trans Type*",     "trans_type",           True,  "str",   {"width": 18, "options": _trans_type_options(),
                                                                     "accept": vr.accepted_spellings(_trans_type_options()),
                                                                     "example": "Supplier Payment"}),
        ("Description*",    "remark",               True,  "str",   {"width": 40, "example": "Settlement of invoice 1042"}),
        ("Amount*",         "amount",               True,  "float", {"width": 14, "example": 250000}),
        ("Party Type",      "party_type",           False, "str",   {"width": 12, "note": "Blank = derived from Trans Type "
                                                                     "(Supplier / Customer / Account)."}),
        ("Party*",          "party",                True,  "str",   {"width": 28, "note": "Supplier or Customer ID, or a GL "
                                                                     "Account for Payment / Receipt / Transfer rows."}),
        ("Payee Name",      "payee_name",           False, "str",   {"width": 24}),
        ("Mode of Payment", "mode_of_payment",      False, "str",   {"width": 18, "link": "Mode of Payment"}),
        ("Exch Rate",       "exch_rate",            False, "float", {"width": 10, "note": "Foreign-currency bank accounts only."}),
        ("Amount in FC",    "amount_in_fc",         False, "float", {"width": 14}),
        ("Trans Currency",  "transaction_currency", False, "str",   {"width": 12, "link": "Currency"}),
        ("Cost Center",     "cost_center",          False, "str",   {"width": 24, "link": "Cost Center"}),
        ("Department",      "department",           False, "str",   {"width": 18, "link": "Department"}),
        ("Branch",          "branch",               False, "str",   {"width": 16, "link": "Branch"}),
        ("Customer ID",     "customer_id",          False, "str",   {"width": 18, "link": "Customer"}),
    ]


_STATUS_COLUMNS = [
    ("Inflow", "inflow", 14), ("Outflow", "outflow", 14), ("Balance", "balance", 14),
    ("Entry Created", "_created", 14), ("Entry Type", "entry_type_created", 16),
    ("Entry Reference", "entry_reference", 22),
]


class BatchBankTransaction(Document):
    """
    Batch Bank Transaction Document Controller
    Handles batch processing of bank transactions.  What a row becomes
    (Payments / Receipts vouchers, or Journal / Payment Entry) is decided by
    the document's Posting Policy through voucher_router.
    """

    def validate(self):
        """Validate document before saving"""
        self.set_default_policy()
        self.set_flows()
        self.validate_bank_account()
        self.validate_transactions()
        self.validate_duplicate_references()
        self.calculate_totals()
        self.validate_balance()

    def before_submit(self):
        """Actions before submitting"""
        self.validate_all_transactions_complete()
        self.check_posting_restrictions()

    def on_submit(self):
        """Actions on submit - create the entries chosen by the Posting Policy"""
        if self.post_batch:
            made = self.post_rows()
            self.update_bank_balance()
            frappe.msgprint(_("Batch posted successfully. {0} entries created as Draft.").format(made),
                            indicator='green')

    def on_cancel(self):
        """Actions on cancel - Cancel related documents"""
        self.cancel_related_documents()
        frappe.msgprint(_("Batch cancelled and related documents removed."), indicator='orange')

    # ========================================
    # POLICY / ROW NORMALISATION
    # ========================================

    def set_default_policy(self):
        # Batches saved before the field existed keep creating Payments / Receipts.
        self.posting_policy = vr.resolve_policy(self.get("posting_policy"), default=vr.POLICY_VOUCHERS)

    def set_flows(self):
        """Server-side source of truth for Party Type and Inflow / Outflow, so
        imported rows behave exactly like rows keyed in on the form."""
        for row in self.get("transaction_entry", []):
            tt = vr.canonical(row.trans_type)
            if not row.party_type and vr.party_type_for(tt):
                row.party_type = vr.party_type_for(tt)
            amt = flt(row.amount)
            if tt in vr.INFLOW_TYPES:
                row.inflow, row.outflow = amt, 0
            elif tt in vr.OUTFLOW_TYPES:
                row.inflow, row.outflow = 0, amt

    # ========================================
    # VALIDATION METHODS
    # ========================================
    
    def validate_bank_account(self):
        """Validate bank account exists and is active"""
        if not self.bank_account:
            frappe.throw(_("Bank Account is mandatory"))
        
        bank_account = frappe.get_doc("Bank Account", self.bank_account)
        if bank_account.disabled:
            frappe.throw(_("Bank Account {0} is disabled").format(self.bank_account))
    
    def validate_transactions(self):
        """Validate individual transactions"""
        if not self.transaction_entry:
            frappe.throw(_("Please add at least one transaction"))
        
        for idx, row in enumerate(self.transaction_entry):
            # Validate required fields
            if not row.posting_date:
                frappe.throw(_("Row {0}: Posting Date is mandatory").format(idx + 1))
            
            if not row.trans_type:
                frappe.throw(_("Row {0}: Transaction Type is mandatory").format(idx + 1))
            
            if not row.amount or row.amount <= 0:
                frappe.throw(_("Row {0}: Amount must be greater than 0").format(idx + 1))
            
            if not row.party:
                frappe.throw(_("Row {0}: Party is mandatory").format(idx + 1))
            
            # Validate party type matches party
            self.validate_party_type(row, idx)
            
            # Validate date is not future
            if getdate(row.posting_date) > getdate(today()):
                frappe.throw(_("Row {0}: Posting date cannot be in future").format(idx + 1))
    
    def validate_party_type(self, row, idx):
        """Validate party type matches the selected party"""
        if row.party_type and row.party:
            if row.party_type in ["Customer", "Supplier"]:
                if not frappe.db.exists(row.party_type, row.party):
                    frappe.throw(_("Row {0}: {1} {2} does not exist").format(
                        idx + 1, row.party_type, row.party
                    ))
            elif row.party_type == "Account":
                if not frappe.db.exists("Account", row.party):
                    frappe.throw(_("Row {0}: Account {1} does not exist").format(
                        idx + 1, row.party
                    ))
    

    def validate_duplicate_references(self):
        """Check for duplicate reference numbers in the system"""
        policy = self.posting_policy
        for row in self.transaction_entry:
            if not row.name or row.get("entry_reference"):
                continue
            ref_no = row.name[-7:].upper()
            if policy == vr.POLICY_VOUCHERS:
                checks = (("Payments", {"reference_no": ref_no}), ("Receipts", {"reference_no": ref_no}))
            else:
                checks = (("Journal Entry", {"cheque_no": ref_no}), ("Payment Entry", {"reference_no": ref_no}))
            for dt, flt_ in checks:
                flt_["docstatus"] = ["<", 2]
                if frappe.db.exists(dt, flt_):
                    frappe.throw(_("Reference number {0} already exists in {1}. "
                                   "This batch may have been posted already.").format(ref_no, dt))

    def calculate_totals(self):
        """Calculate total inflow, outflow and balance"""
        total_inflow = 0
        total_outflow = 0
        balance = flt(self.opening_balance)
        
        for row in self.transaction_entry:
            total_inflow += flt(row.inflow)
            total_outflow += flt(row.outflow)
            balance += flt(row.inflow) - flt(row.outflow)
            row.balance = balance
        
        self.total_inflow = total_inflow
        self.total_outflow = total_outflow
        self.balance = balance
    
    def validate_balance(self):
        """Validate that balance calculations are correct"""
        calculated_balance = flt(self.opening_balance) + flt(self.total_inflow) - flt(self.total_outflow)
        
        if abs(calculated_balance - flt(self.balance)) > 0.01:
            frappe.throw(_("Balance calculation error. Expected {0}, got {1}").format(
                calculated_balance, self.balance
            ))
    
    def validate_all_transactions_complete(self):
        """Validate all transactions have complete information before submit"""
        incomplete = []
        default_cc = frappe.db.get_value("Company", self.company, "cost_center")

        for idx, row in enumerate(self.transaction_entry, start=1):
            # Validate Remark
            if not row.remark or len(row.remark.strip()) < 5:
                incomplete.append(_("Row {0}: Insufficient remark").format(idx))

            # Validate / Auto-set Cost Center
            if not row.cost_center:
                # Auto-assign only
                row.cost_center = default_cc

                # If still missing after auto-assign, then notify
                if not row.cost_center:
                    incomplete.append(_("Row {0}: Cost Center is mandatory").format(idx))

        # Throw aggregated errors
        if incomplete:
            frappe.throw("<br>".join([frappe.bold(msg) for msg in incomplete]))
    
    def check_posting_restrictions(self):
        """Check if posting is allowed for the selected period"""
        from erpnext.accounts.utils import get_fiscal_year
        
        for idx, row in enumerate(self.transaction_entry):
            try:
                fiscal_year = get_fiscal_year(row.posting_date, company=self.company)[0]
            except Exception as e:
                frappe.throw(_("Row {0}: {1}").format(idx + 1, str(e)))
    

    # ========================================
    # POSTING  (replaces the 9 create_* methods)
    # ========================================

    def _line(self, row):
        """Child row -> router line."""
        tt = vr.canonical(row.trans_type)
        party_type = row.party_type or vr.party_type_for(tt)
        line = {
            "idx": row.idx,
            "trans_type": tt,
            "posting_date": row.posting_date,
            "amount": flt(row.amount),
            "amount_in_fc": flt(row.get("amount_in_fc")),
            "exch_rate": flt(row.get("exch_rate")),
            "transaction_currency": row.get("transaction_currency"),
            "remark": (row.remark or "").strip(),
            "party_type": party_type,
            "party_name": row.get("party_name"),
            "payee_name": (row.get("payee_name") or "").title(),
            "mode_of_payment": row.get("mode_of_payment"),
            "reference_no": row.name[-7:].upper(),
            "cost_center": row.get("cost_center"),
            "department": row.get("department"),
            "branch": row.get("branch"),
            "customer_id": row.get("customer_id"),
            "issued_by": self.get("batch_owner") or frappe.session.user,
            "amortise": row.get("amortise"),
            "frequency": row.get("frequency"),
            "no_of_periods": row.get("no_of_periods"),
            "start_date": row.get("start_date"),
        }
        # Customer / Supplier rows carry the party; Payment / Receipt / Transfer
        # rows carry a GL account in the same column.
        if party_type == "Account":
            line["counter_account"] = row.party
        else:
            line["party"] = row.party
        return line

    def post_rows(self):
        """
        Create one document per row according to the Posting Policy.
        Idempotent (rows already linked are skipped) and all-or-nothing: any
        row failing aborts the submit with the full list of problems.
        """
        policy = self.posting_policy
        made, errors = 0, []
        for row in self.transaction_entry:
            if row.get("entry_reference"):
                continue
            try:
                name, dt = vr.create_entry(
                    self._line(row), policy, self.company, self.bank_account,
                    source_doctype=self.doctype, source_name=self.name,
                    source_row=row.name, submit=False, default_mode="Wire Transfer")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Batch Bank Transaction {self.name}: row {row.idx}")
                errors.append(str(e) if str(e).startswith("Row ") else _("Row {0}: {1}").format(row.idx, e))
                continue

            values = {"entry_type_created": dt, "entry_reference": name}
            # keep the legacy link columns populated for existing reports
            if dt == "Payments":
                values["payment_entry"] = name
            elif dt == "Receipts":
                values["receipt_entry"] = name
            frappe.db.set_value(row.doctype, row.name, values, update_modified=False)
            made += 1

        if errors:
            frappe.throw("<br>".join(errors[:10]) + (f"<br>... and {len(errors) - 10} more" if len(errors) > 10 else ""),
                         title=_("Batch not posted - fix these rows"))
        return made

    def update_bank_balance(self):
        """Update bank account balance after posting"""
        # This would integrate with your bank reconciliation module
        pass

    def cancel_related_documents(self):
        """Cancel everything this batch created (Payments, Receipts, Journal
        Entries, Payment Entries), whichever policy was used."""
        # 1. Row-linked documents (new rows + legacy payment_entry / receipt_entry)
        for row in self.transaction_entry:
            pairs = {(row.get("entry_type_created"), row.get("entry_reference"))}
            if row.get("payment_entry"):
                pairs.add(("Payments", row.get("payment_entry")))
            if row.get("receipt_entry"):
                pairs.add(("Receipts", row.get("receipt_entry")))
            for dt, name in pairs:
                try:
                    vr.cancel_or_delete(dt, name)
                except Exception:
                    frappe.log_error(frappe.get_traceback(), f"Batch Bank Transaction {self.name}: cancel {dt} {name}")
                    frappe.throw(_("Could not cancel {0} {1}. Cancel it manually first.").format(dt, name))

        # 2. Legacy documents tagged with this batch (unchanged behaviour)
        for dt in ("Journal Entry", "Payment Entry"):
            for d in frappe.get_all(dt, filters={"reference_document_no": self.name, "docstatus": 1},
                                    fields=["name"]):
                frappe.get_doc(dt, d.name).cancel()

        # 3. Auto Repeat documents
        auto_repeats = frappe.get_all("Auto Repeat",
            filters={"reference_document": self.name, "docstatus": 1},
            fields=["name"])
        for ar in auto_repeats:
            doc = frappe.get_doc("Auto Repeat", ar.name)
            doc.cancel()


# ========================================
# EXCEL TEMPLATE / EXPORT / IMPORT
# ========================================

@frappe.whitelist()
def download_template():
    b64 = xio.build_workbook(_SHEET, _columns(), template=True)
    return {"filename": "Batch_Bank_Transaction_Template.xlsx", "file_content": b64}


@frappe.whitelist()
def export_to_excel(doc_name):
    """Export in the SAME layout import reads, so a file can be edited and re-imported."""
    doc = frappe.get_doc("Batch Bank Transaction", doc_name)
    doc.check_permission("read")
    cols = _columns()
    rows = []
    for r in doc.transaction_entry:
        rec = {c[1]: r.get(c[1]) for c in cols}
        rec.update({"inflow": flt(r.get("inflow")), "outflow": flt(r.get("outflow")),
                    "balance": flt(r.get("balance")),
                    "_created": "YES" if r.get("entry_reference") else "NO",
                    "entry_type_created": r.get("entry_type_created") or "",
                    "entry_reference": r.get("entry_reference") or "",
                    "_done": bool(r.get("entry_reference"))})
        rows.append(rec)
    info = [
        ("Batch", doc.name), ("Company", doc.get("company") or ""),
        ("Bank Account", doc.bank_account or ""), ("Currency", doc.get("bank_account_currency") or ""),
        ("Posting Policy", doc.get("posting_policy") or ""),
        ("Opening Balance", flt(doc.opening_balance)), ("Total Inflow", flt(doc.total_inflow)),
        ("Total Outflow", flt(doc.total_outflow)), ("Closing Balance", flt(doc.balance)),
        ("Rows", len(doc.transaction_entry)), ("Exported By", frappe.session.user),
        ("Exported At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]
    b64 = xio.build_workbook(_SHEET, cols, rows, _STATUS_COLUMNS, info)
    return {"filename": f"BBT_{doc.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "file_content": b64}


@frappe.whitelist()
def import_from_excel(doc_name, file_content, filename, replace_existing=0):
    doc = frappe.get_doc("Batch Bank Transaction", doc_name)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw(_("Rows can only be imported into a Draft batch."))

    cols = _columns()
    type_options = _trans_type_options()
    by_canon = {vr.canonical(o): o for o in type_options}

    records, errors, skipped = xio.parse_rows(file_content, filename, _SHEET, cols,
                                              describe_field="remark")
    default_cc = frappe.db.get_value("Company", doc.company, "cost_center") if doc.get("company") else None
    good = []
    for rec in records:
        row_no = rec.pop("_excel_row", None)
        problems = []

        # Trans Type: accept either spelling (Customer Refund / Customer Refunds ...)
        tt = vr.canonical(rec.get("trans_type"))
        if tt not in vr.INFLOW_TYPES | vr.OUTFLOW_TYPES:
            problems.append(f"Trans Type '{rec.get('trans_type')}' is not supported")
        elif by_canon and tt in by_canon:
            rec["trans_type"] = by_canon[tt]

        if flt(rec.get("amount")) <= 0:
            problems.append("Amount must be greater than zero")
        if rec.get("posting_date") and getdate(rec["posting_date"]) > getdate(today()):
            problems.append("Date cannot be in the future")

        ptype = rec.get("party_type") or vr.party_type_for(tt)
        if ptype and rec.get("party") and ptype in ("Customer", "Supplier", "Account"):
            if not frappe.db.exists(ptype, rec["party"]):
                problems.append(f"{ptype} '{rec['party']}' does not exist")
        rec["party_type"] = ptype

        if problems:
            errors.append({"row": row_no, "errors": problems, "description": rec.get("remark") or ""})
            skipped += 1
            continue
        if not rec.get("cost_center") and default_cc:
            rec["cost_center"] = default_cc
        good.append(rec)

    if good:
        if int(replace_existing or 0):
            doc.set("transaction_entry", [])
        for rec in good:
            doc.append("transaction_entry", rec)
        doc.save()
        frappe.db.commit()
    return xio.import_result(len(good), skipped, errors)



@frappe.whitelist()
def get_ai_suggestions(doc_name):
    """
    Get AI-powered suggestions for the batch
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
    
    Returns:
        Dictionary with AI suggestions
    """
    try:
        doc = frappe.get_doc("Batch Bank Transaction", doc_name)
        
        suggestions = {
            "anomalies": detect_anomalies(doc),
            "optimizations": suggest_optimizations(doc),
            "validation_issues": check_validation_issues(doc),
            "duplicate_risks": find_potential_duplicates(doc)
        }
        
        return suggestions
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "AI Suggestions Error")
        return {"error": str(e)}


def detect_anomalies(doc):
    """Detect anomalies in the batch"""
    anomalies = []
    
    if not doc.transaction_entry:
        return anomalies
    
    # Calculate statistics
    amounts = [flt(t.amount) for t in doc.transaction_entry if t.amount]
    if not amounts:
        return anomalies
    
    avg_amount = sum(amounts) / len(amounts)
    
    # Simple standard deviation
    variance = sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)
    std_dev = variance ** 0.5
    
    # Check for outliers (2 standard deviations)
    for idx, trans in enumerate(doc.transaction_entry):
        if flt(trans.amount) > avg_amount + (2 * std_dev):
            anomalies.append({
                "row": idx + 1,
                "type": "large_amount",
                "message": f"Unusually large amount: {frappe.format_value(trans.amount, {'fieldtype': 'Currency'})}",
                "severity": "warning"
            })
        
        # Check for missing critical information
        if not trans.remark or len(trans.remark) < 10:
            anomalies.append({
                "row": idx + 1,
                "type": "insufficient_detail",
                "message": "Insufficient remark detail",
                "severity": "info"
            })
        
        # Check for weekend transactions
        posting_date = getdate(trans.posting_date)
        if posting_date.weekday() >= 5:  # Saturday or Sunday
            anomalies.append({
                "row": idx + 1,
                "type": "weekend_transaction",
                "message": f"Transaction on weekend: {posting_date.strftime('%A, %B %d')}",
                "severity": "info"
            })
    
    return anomalies


def suggest_optimizations(doc):
    """Suggest optimizations for the batch"""
    suggestions = []
    
    # Check for recurring parties
    party_counts = {}
    for trans in doc.transaction_entry:
        if trans.party:
            party_counts[trans.party] = party_counts.get(trans.party, 0) + 1
    
    for party, count in party_counts.items():
        if count >= 3:
            suggestions.append({
                "type": "recurring_party",
                "message": f"Consider setting up recurring transaction for {party} ({count} occurrences)",
                "action": "create_auto_repeat"
            })
    
    # Check for similar amounts
    amount_groups = {}
    for trans in doc.transaction_entry:
        rounded = round(flt(trans.amount) / 1000) * 1000
        if rounded > 0:
            amount_groups[rounded] = amount_groups.get(rounded, 0) + 1
    
    for amount, count in amount_groups.items():
        if count >= 3:
            suggestions.append({
                "type": "similar_amounts",
                "message": f"Multiple transactions around {frappe.format_value(amount, {'fieldtype': 'Currency'})} - consider bulk processing",
                "action": "bulk_process"
            })
    
    # Check if all transactions use same cost center
    cost_centers = set(t.cost_center for t in doc.transaction_entry if t.cost_center)
    if len(cost_centers) == 1:
        suggestions.append({
            "type": "single_cost_center",
            "message": "All transactions use the same cost center - consider setting it at batch level",
            "action": "set_batch_default"
        })
    
    return suggestions


def check_validation_issues(doc):
    """Check for validation issues"""
    issues = []
    
    for idx, trans in enumerate(doc.transaction_entry):
        # Check mandatory fields
        if not trans.posting_date:
            issues.append({
                "row": idx + 1,
                "field": "posting_date",
                "message": "Missing posting date",
                "severity": "error"
            })
        
        if not trans.trans_type:
            issues.append({
                "row": idx + 1,
                "field": "trans_type",
                "message": "Missing transaction type",
                "severity": "error"
            })
        
        if not trans.amount or trans.amount <= 0:
            issues.append({
                "row": idx + 1,
                "field": "amount",
                "message": "Invalid amount",
                "severity": "error"
            })
        
        if not trans.party:
            issues.append({
                "row": idx + 1,
                "field": "party",
                "message": "Missing party",
                "severity": "error"
            })
        
        if not trans.remark:
            issues.append({
                "row": idx + 1,
                "field": "remark",
                "message": "Missing remark",
                "severity": "warning"
            })
        
        # Check for future dates
        if trans.posting_date and getdate(trans.posting_date) > getdate(today()):
            issues.append({
                "row": idx + 1,
                "field": "posting_date",
                "message": "Future date not allowed",
                "severity": "error"
            })
    
    return issues


def find_potential_duplicates(doc):
    """Find potential duplicate transactions"""
    duplicates = []
    seen = {}
    
    for idx, trans in enumerate(doc.transaction_entry):
        key = f"{trans.posting_date}_{trans.party}_{flt(trans.amount)}"
        
        if key in seen:
            duplicates.append({
                "row1": seen[key] + 1,
                "row2": idx + 1,
                "date": trans.posting_date,
                "party": trans.party,
                "amount": trans.amount,
                "confidence": 0.9
            })
        else:
            seen[key] = idx
    
    return duplicates


@frappe.whitelist()
def auto_categorize_transaction(remark):
    """
    Auto-categorize transaction based on remark using AI
    
    Args:
        remark: Transaction remark/description
    
    Returns:
        Dictionary with suggested account and confidence score
    """
    if not remark:
        return None
    
    remark_lower = remark.lower()
    
    # AI categorization rules
    categories = [
        {
            "keywords": ['transport', 'fare', 'uber', 'taxi', 'delivery', 'shipping'],
            "account": '8027 - Transportation expenses',
            "confidence": 0.95
        },
        {
            "keywords": ['airtime', 'telephone', 'cug', 'phone', 'call', 'mobile'],
            "account": '8008 - Telephone expenses',
            "confidence": 0.90
        },
        {
            "keywords": ['fuel', 'fueling', 'petrol', 'diesel', 'gas'],
            "account": '8003 - Vehicle fueling expenses',
            "confidence": 0.92
        },
        {
            "keywords": ['water', 'meal', 'lunch', 'dinner', 'food', 'subsidy'],
            "account": '8006 - Meal expenses',
            "confidence": 0.88
        },
        {
            "keywords": ['stationery', 'paper', 'printing', 'office supplies'],
            "account": '8016 - Printing and stationeries',
            "confidence": 0.85
        },
        {
            "keywords": ['rent', 'lease', 'accommodation', 'housing'],
            "account": '8010 - Rent expenses',
            "confidence": 0.90
        },
        {
            "keywords": ['internet', 'wifi', 'broadband', 'data'],
            "account": '8009 - Internet expenses',
            "confidence": 0.87
        },
        {
            "keywords": ['electricity', 'power', 'nepa', 'phcn'],
            "account": '8011 - Electricity expenses',
            "confidence": 0.92
        },
        {
            "keywords": ['insurance', 'premium', 'coverage'],
            "account": '8012 - Insurance expenses',
            "confidence": 0.88
        },
        {
            "keywords": ['repair', 'maintenance', 'fixing'],
            "account": '8013 - Repairs and maintenance',
            "confidence": 0.85
        }
    ]
    
    best_match = None
    best_confidence = 0
    
    for category in categories:
        for keyword in category["keywords"]:
            if keyword in remark_lower:
                if category["confidence"] > best_confidence:
                    best_match = category["account"]
                    best_confidence = category["confidence"]
    
    if best_match and best_confidence > 0.80:
        return {
            "account": best_match,
            "confidence": best_confidence,
            "reason": "AI categorization based on remark analysis"
        }
    
    return None


@frappe.whitelist()
def get_bank_balance(bank_account, as_on_date=None):
    """
    Get bank balance as on a specific date
    
    Args:
        bank_account: Bank Account name
        as_on_date: Date for balance check (default: today)
    
    Returns:
        Dictionary with balance information
    """
    if not as_on_date:
        as_on_date = today()
    
    bank_account_doc = frappe.get_doc("Bank Account", bank_account)
    account = bank_account_doc.account
    
    balance = frappe.db.sql("""
        SELECT 
            SUM(debit) - SUM(credit) as balance
        FROM `tabGL Entry`
        WHERE account = %s 
        AND posting_date <= %s
        AND is_cancelled = 0
    """, (account, as_on_date), as_dict=1)[0]
    
    return {
        "account": account,
        "balance": flt(balance.balance) if balance else 0,
        "as_on_date": as_on_date,
        "currency": bank_account_doc.account_currency
    }


@frappe.whitelist()
def reconcile_batch(doc_name):
    """
    Reconcile batch with actual bank statement
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
    
    Returns:
        Dictionary with reconciliation status
    """
    doc = frappe.get_doc("Batch Bank Transaction", doc_name)
    
    # Get current bank balance
    bank_balance = get_bank_balance(doc.bank_account, doc.batch_date)
    
    # Calculate expected balance
    expected_balance = flt(doc.opening_balance) + flt(doc.total_inflow) - flt(doc.total_outflow)
    
    difference = expected_balance - flt(bank_balance["balance"])
    
    return {
        "status": "matched" if abs(difference) < 0.01 else "mismatch",
        "expected_balance": expected_balance,
        "actual_balance": bank_balance["balance"],
        "difference": difference,
        "currency": doc.bank_account_currency
    }


@frappe.whitelist()
def bulk_update_cost_center(doc_name, cost_center):
    """
    Bulk update cost center for all transactions
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
        cost_center: Cost Center to set
    
    Returns:
        Success message
    """
    doc = frappe.get_doc("Batch Bank Transaction", doc_name)
    
    if doc.docstatus != 0:
        frappe.throw(_("Cannot update submitted document"))
    
    for trans in doc.transaction_entry:
        trans.cost_center = cost_center
    
    doc.save()
    
    return {
        "success": True,
        "message": f"Updated {len(doc.transaction_entry)} transactions with cost center {cost_center}"
    }


@frappe.whitelist()
def generate_batch_report(doc_name):
    """
    Generate comprehensive batch report
    
    Args:
        doc_name: Name of the Batch Bank Transaction document
    
    Returns:
        Dictionary with report data
    """
    doc = frappe.get_doc("Batch Bank Transaction", doc_name)
    
    # Transaction type breakdown
    type_breakdown = {}
    for trans in doc.transaction_entry:
        trans_type = trans.trans_type
        type_breakdown[trans_type] = type_breakdown.get(trans_type, 0) + 1
    
    # Party breakdown
    party_breakdown = {}
    for trans in doc.transaction_entry:
        if trans.party:
            if trans.party not in party_breakdown:
                party_breakdown[trans.party] = {"count": 0, "total_amount": 0}
            party_breakdown[trans.party]["count"] += 1
            party_breakdown[trans.party]["total_amount"] += flt(trans.amount)
    
    # Daily breakdown
    daily_breakdown = {}
    for trans in doc.transaction_entry:
        date = cstr(trans.posting_date)
        if date not in daily_breakdown:
            daily_breakdown[date] = {"inflow": 0, "outflow": 0, "count": 0}
        daily_breakdown[date]["inflow"] += flt(trans.inflow)
        daily_breakdown[date]["outflow"] += flt(trans.outflow)
        daily_breakdown[date]["count"] += 1
    
    return {
        "summary": {
            "total_transactions": len(doc.transaction_entry),
            "total_inflow": doc.total_inflow,
            "total_outflow": doc.total_outflow,
            "net_balance": doc.balance,
            "opening_balance": doc.opening_balance
        },
        "type_breakdown": type_breakdown,
        "party_breakdown": party_breakdown,
        "daily_breakdown": daily_breakdown
    }


# ========================================
# SCHEDULED JOBS
# ========================================

def process_recurring_transactions():
    """
    Process recurring transactions (to be run as scheduled job)
    """
    # Get all active recurring transactions
    recurring_trans = frappe.db.sql("""
        SELECT 
            parent, name, posting_date, next_posting_date, 
            charged_amount, frequency, no_of_periods
        FROM `tabTransaction Entry`
        WHERE frequency IS NOT NULL
        AND next_posting_date <= %s
        AND (end_date IS NULL OR end_date >= %s)
    """, (today(), today()), as_dict=1)
    
    for trans in recurring_trans:
        try:
            # Create new transaction entry
            create_recurring_entry(trans)
            
            # Update next posting date
            update_next_posting_date(trans)
            
        except Exception as e:
            frappe.log_error(f"Error processing recurring transaction {trans.name}: {str(e)}")


def create_recurring_entry(trans):
    """Create new entry from recurring transaction"""
    # Implementation for creating recurring entries
    pass


def update_next_posting_date(trans):
    """Update next posting date for recurring transaction"""
    # Implementation for updating next date
    pass




def validate_party_name(doc, method):
    """Validate and update party names"""
    for entry in doc.transaction_entry:
        if entry.trans_type == "Supplier Payment" and entry.party:
            entry.party_name = frappe.db.get_value('Supplier', entry.party, 'supplier_name')
        elif entry.trans_type == "Customer Receipt" and entry.party:
            entry.party_name = frappe.db.get_value('Customer', entry.party, 'customer_name')


def update_party_names(doc, method):
    """Update party names before saving"""
    for entry in doc.transaction_entry:
        if entry.party_type == "Supplier" and entry.party:
            supplier_name = frappe.db.get_value('Supplier', entry.party, 'supplier_name')
            if supplier_name:
                entry.party_name = supplier_name
                entry.payee_name = supplier_name
        
        elif entry.party_type == "Customer" and entry.party:
            customer_name = frappe.db.get_value('Customer', entry.party, 'customer_name')
            if customer_name:
                entry.party_name = customer_name
                entry.payee_name = customer_name


def on_batch_submit(doc, method):
    """Handle batch submission"""
    # Send notification to relevant users
    notify_batch_submission(doc)
    
    # Create dashboard update
    update_dashboard_metrics(doc)


def on_batch_cancel(doc, method):
    """Handle batch cancellation"""
    # Send notification
    notify_batch_cancellation(doc)


def notify_batch_submission(doc):
    """Send notification when batch is submitted"""
    # Get relevant users
    users_to_notify = get_notification_users(doc)
    
    for user in users_to_notify:
        frappe.publish_realtime(
            event='batch_submitted',
            message={
                'batch_name': doc.name,
                'bank_account': doc.bank_account,
                'total_amount': doc.total_inflow + doc.total_outflow,
                'transaction_count': len(doc.transaction_entry)
            },
            user=user
        )


def notify_batch_cancellation(doc):
    """Send notification when batch is cancelled"""
    users_to_notify = get_notification_users(doc)
    
    for user in users_to_notify:
        frappe.publish_realtime(
            event='batch_cancelled',
            message={
                'batch_name': doc.name,
                'bank_account': doc.bank_account
            },
            user=user
        )


def get_notification_users(doc):
    """Get list of users to notify"""
    users = []
    
    # Add batch owner
    if doc.batch_owner:
        users.append(doc.batch_owner)
    
    # Add users with specific roles
    accounts_managers = frappe.get_all("Has Role",
        filters={"role": "Accounts Manager", "parenttype": "User"},
        fields=["parent"])
    
    users.extend([u.parent for u in accounts_managers])
    
    return list(set(users))  # Remove duplicates


def update_dashboard_metrics(doc):
    """Update dashboard metrics after batch submission"""
    # This can be used to update custom dashboards
    pass


def send_batch_reminders():
    """Send reminders for pending batches (scheduled hourly)"""
    # Get draft batches older than 24 hours
    pending_batches = frappe.get_all("Batch Bank Transaction",
        filters={
            "docstatus": 0,
            "creation": ["<", frappe.utils.add_to_date(today(), hours=-24)]
        },
        fields=["name", "batch_owner", "bank_account"])
    
    for batch in pending_batches:
        if batch.batch_owner:
            # Send email reminder
            frappe.sendmail(
                recipients=[batch.batch_owner],
                subject=f"Reminder: Pending Batch Bank Transaction - {batch.name}",
                message=f"""
                    <p>Dear User,</p>
                    <p>You have a pending Batch Bank Transaction that has not been submitted:</p>
                    <ul>
                        <li><strong>Batch:</strong> {batch.name}</li>
                        <li><strong>Bank Account:</strong> {batch.bank_account}</li>
                    </ul>
                    <p>Please review and submit the batch at your earliest convenience.</p>
                """,
                reference_doctype="Batch Bank Transaction",
                reference_name=batch.name
            )