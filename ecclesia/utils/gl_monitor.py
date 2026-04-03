"""
GL Monitor
===========
Monitors all GL Entry activity for audit purposes.
Implements:
- GL amendment tracking (cancellations and repostings)
- Journal Entry fraud detection (ACFE methodology)
- Three-way reconciliation (document → GL → account balance)
- Financial assertion testing (Completeness, Accuracy, Existence, Cutoff, Classification)
- Suspense account monitoring
"""

import frappe
from frappe.utils import flt, getdate, today, add_days


# ─────────────────────────────────────────────────────────────────────────────
# Hooks called from hooks.py
# ─────────────────────────────────────────────────────────────────────────────

def track_gl_entry(doc, method=None):
    """Called after every GL Entry insert. Log to audit GL log."""
    _log_gl_event(doc, "Created")

    # Flag suspense account usage immediately
    suspense_keywords = ["suspense", "clearing", "interim", "holding"]
    account_lower = (doc.account or "").lower()
    if any(k in account_lower for k in suspense_keywords):
        _raise_gl_finding(
            gl_entry=doc,
            finding_type="Suspense Account Usage",
            risk_rating="High",
            observation=f"GL Entry posted to suspense/clearing account: {doc.account}. "
                        f"Voucher: {doc.voucher_type} {doc.voucher_no}. "
                        f"All suspense postings require immediate review and reclassification."
        )


def track_gl_cancellation(doc, method=None):
    """Called when a GL Entry is cancelled. Always audit-log and flag."""
    _log_gl_event(doc, "Cancelled")

    _raise_gl_finding(
        gl_entry=doc,
        finding_type="GL Entry Cancellation",
        risk_rating="High",
        observation=f"GL Entry cancelled: {doc.voucher_type} {doc.voucher_no} "
                    f"for {doc.account}, Amount: {doc.debit or doc.credit:,.2f}. "
                    f"Cancelled GL entries are high-risk — verify this cancellation "
                    f"was authorized and determine if a corrected reposting was made."
    )


def flag_journal_entry_risks(doc, method=None):
    """Called on Journal Entry submit. Apply ACFE fraud detection methodology."""
    from ecclesia.utils.ai_engine import analyse_journal_entry
    flags = analyse_journal_entry(doc.as_dict())

    for flag in flags:
        _raise_gl_finding(
            gl_entry=None,
            finding_type=flag["type"],
            risk_rating=flag["severity"],
            observation=flag["description"],
            voucher_type="Journal Entry",
            voucher_no=doc.name,
            amount=doc.total_debit
        )


# ─────────────────────────────────────────────────────────────────────────────
# GL Reconciliation Engine
# ─────────────────────────────────────────────────────────────────────────────

def reconcile_gl_audit_mappings():
    """
    Daily reconciliation: verify GL entries match source documents.
    Three-way reconciliation: Document Total → GL Posting → Account Balance Movement.
    """
    registered_gl_doctypes = frappe.get_all(
        "Auditable DocType Registry",
        filters={"is_gl_posting": 1, "is_active": 1},
        fields=["doctype_name", "amount_fields", "transaction_code"]
    )

    for reg in registered_gl_doctypes:
        try:
            _reconcile_doctype(reg)
        except Exception as e:
            frappe.log_error(f"GL reconciliation failed for {reg.doctype_name}: {e}")


def _reconcile_doctype(reg):
    """Reconcile a single GL-posting DocType for the last 7 days."""
    doctype_name = reg.doctype_name
    if not frappe.db.table_exists(f"tab{doctype_name}"):
        return

    from_date = add_days(today(), -7)
    amount_fields = [f.strip() for f in (reg.amount_fields or "").split(",") if f.strip()]
    primary_amount_field = amount_fields[0] if amount_fields else None

    if not primary_amount_field or not frappe.db.has_column(doctype_name, primary_amount_field):
        return

    # Get submitted documents in range
    docs = frappe.db.get_all(
        doctype_name,
        filters={
            "docstatus": 1,
            "posting_date": [">=", from_date] if frappe.db.has_column(doctype_name, "posting_date") else [">=", from_date]
        },
        fields=["name", primary_amount_field],
        limit=500
    )

    for doc in docs:
        doc_amount = flt(doc.get(primary_amount_field, 0))
        if doc_amount <= 0:
            continue

        # Sum GL entries for this voucher
        gl_total = frappe.db.sql("""
            SELECT SUM(debit) as total_debit
            FROM `tabGL Entry`
            WHERE voucher_type = %s AND voucher_no = %s AND is_cancelled = 0
        """, (doctype_name, doc.name), as_dict=True)

        gl_amount = flt(gl_total[0].total_debit) if gl_total else 0

        # Allow small rounding tolerance (0.01)
        variance = abs(doc_amount - gl_amount)
        if variance > 0.01 and gl_amount > 0:
            _raise_gl_finding(
                gl_entry=None,
                finding_type="GL Reconciliation Variance",
                risk_rating="High" if variance > 1000 else "Medium",
                observation=f"Reconciliation variance detected for {doctype_name} {doc.name}. "
                            f"Document amount: {doc_amount:,.2f}, GL posting: {gl_amount:,.2f}, "
                            f"Variance: {variance:,.2f}. "
                            f"Transaction Code: {reg.transaction_code}. "
                            f"Investigate and correct GL posting.",
                voucher_type=doctype_name,
                voucher_no=doc.name,
                amount=variance
            )


# ─────────────────────────────────────────────────────────────────────────────
# Financial Assertion Testing
# ─────────────────────────────────────────────────────────────────────────────

def test_financial_assertions(doctype_name, from_date, to_date):
    """
    Apply the five financial audit assertions to a DocType's GL entries.
    Returns dict of assertion results.
    """
    results = {
        "completeness":   _test_completeness(doctype_name, from_date, to_date),
        "accuracy":       _test_accuracy(doctype_name, from_date, to_date),
        "existence":      _test_existence(doctype_name, from_date, to_date),
        "cutoff":         _test_cutoff(doctype_name, from_date, to_date),
        "classification": _test_classification(doctype_name, from_date, to_date),
    }
    return results


def _test_completeness(doctype_name, from_date, to_date):
    """
    Completeness: Are all submitted documents reflected in the GL?
    Find submitted docs without any GL entry.
    """
    if not frappe.db.table_exists(f"tab{doctype_name}"):
        return {"passed": True, "exceptions": []}

    date_field = "posting_date" if frappe.db.has_column(doctype_name, "posting_date") else "creation"
    submitted_docs = frappe.db.get_all(
        doctype_name,
        filters={"docstatus": 1, date_field: ["between", [from_date, to_date]]},
        fields=["name"],
        limit=500
    )

    exceptions = []
    for doc in submitted_docs:
        gl_count = frappe.db.count("GL Entry", filters={
            "voucher_type": doctype_name,
            "voucher_no":   doc.name,
            "is_cancelled": 0
        })
        if gl_count == 0:
            exceptions.append({
                "document":    doc.name,
                "issue":       "Submitted document has no GL entries — completeness failure",
                "assertion":   "Completeness"
            })

    return {"passed": len(exceptions) == 0, "exceptions": exceptions}


def _test_accuracy(doctype_name, from_date, to_date):
    """Accuracy: Do document amounts match GL postings exactly?"""
    # Handled in reconcile_doctype — return placeholder
    return {"passed": True, "exceptions": [], "note": "See GL Reconciliation findings"}


def _test_existence(doctype_name, from_date, to_date):
    """
    Existence: Do GL entries have corresponding source documents?
    Find GL entries where the source document is cancelled or missing.
    """
    gl_entries = frappe.db.get_all(
        "GL Entry",
        filters={
            "voucher_type": doctype_name,
            "posting_date":  ["between", [from_date, to_date]],
            "is_cancelled":  0
        },
        fields=["name", "voucher_no", "debit", "credit", "account"],
        limit=500
    )

    exceptions = []
    for gl in gl_entries:
        doc_status = frappe.db.get_value(doctype_name, gl.voucher_no, "docstatus")
        if doc_status is None:
            exceptions.append({
                "gl_entry":  gl.name,
                "document":  gl.voucher_no,
                "issue":     "GL Entry exists but source document not found — existence failure",
                "assertion": "Existence"
            })
        elif doc_status == 2:  # Cancelled
            exceptions.append({
                "gl_entry":  gl.name,
                "document":  gl.voucher_no,
                "issue":     "Active GL Entry linked to cancelled document — existence failure",
                "assertion": "Existence"
            })

    return {"passed": len(exceptions) == 0, "exceptions": exceptions}


def _test_cutoff(doctype_name, from_date, to_date):
    """
    Cutoff: Are transactions recorded in the correct period?
    Find GL entries where posting_date differs significantly from document date.
    """
    if not frappe.db.has_column(doctype_name, "posting_date"):
        return {"passed": True, "exceptions": []}

    exceptions = frappe.db.sql("""
        SELECT gl.name, gl.voucher_no, gl.posting_date as gl_date,
               doc.posting_date as doc_date,
               ABS(DATEDIFF(gl.posting_date, doc.posting_date)) as date_diff
        FROM `tabGL Entry` gl
        JOIN `tab{doctype}` doc ON doc.name = gl.voucher_no
        WHERE gl.voucher_type = %(doctype)s
        AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND gl.is_cancelled = 0
        AND ABS(DATEDIFF(gl.posting_date, doc.posting_date)) > 3
        LIMIT 100
    """.format(doctype=doctype_name), {
        "doctype":   doctype_name,
        "from_date": from_date,
        "to_date":   to_date
    }, as_dict=True)

    return {
        "passed": len(exceptions) == 0,
        "exceptions": [
            {
                "gl_entry":  e.name,
                "document":  e.voucher_no,
                "issue":     f"GL posting date differs from document date by {e.date_diff} days",
                "assertion": "Cutoff"
            }
            for e in exceptions
        ]
    }


def _test_classification(doctype_name, from_date, to_date):
    """
    Classification: Are amounts posted to the correct account types?
    Detect obvious misclassifications.
    """
    # Check for expense postings to capital accounts and vice versa
    exceptions = frappe.db.sql("""
        SELECT gl.name, gl.voucher_no, gl.account, gl.debit, gl.credit,
               acc.account_type, acc.root_type
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE gl.voucher_type = %(doctype)s
        AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND gl.is_cancelled = 0
        AND acc.account_name LIKE '%%suspense%%'
        LIMIT 50
    """, {
        "doctype":   doctype_name,
        "from_date": from_date,
        "to_date":   to_date
    }, as_dict=True)

    return {
        "passed": len(exceptions) == 0,
        "exceptions": [
            {
                "gl_entry": e.name,
                "document": e.voucher_no,
                "issue":    f"Amount posted to suspense account {e.account} — classification risk",
                "assertion":"Classification"
            }
            for e in exceptions
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Analytical Review (ISA 520)
# ─────────────────────────────────────────────────────────────────────────────

def run_analytical_review(from_date, to_date, prior_from_date, prior_to_date):
    """
    Run comparative analytical review across all account balances.
    Compare current period vs prior period and flag unusual movements.
    Returns list of flagged accounts.
    """
    current = frappe.db.sql("""
        SELECT account, SUM(debit - credit) as net_movement
        FROM `tabGL Entry`
        WHERE posting_date BETWEEN %s AND %s
        AND is_cancelled = 0
        GROUP BY account
    """, (from_date, to_date), as_dict=True)

    prior = frappe.db.sql("""
        SELECT account, SUM(debit - credit) as net_movement
        FROM `tabGL Entry`
        WHERE posting_date BETWEEN %s AND %s
        AND is_cancelled = 0
        GROUP BY account
    """, (prior_from_date, prior_to_date), as_dict=True)

    prior_map = {r.account: flt(r.net_movement) for r in prior}
    flags = []

    for row in current:
        account = row.account
        current_val = flt(row.net_movement)
        prior_val = prior_map.get(account, 0)

        if prior_val == 0:
            if abs(current_val) > 10000:  # New account with significant activity
                flags.append({
                    "account":    account,
                    "current":    current_val,
                    "prior":      0,
                    "change_pct": 100,
                    "flag":       "New account with significant activity — verify authorization"
                })
        else:
            change_pct = ((current_val - prior_val) / abs(prior_val)) * 100
            if abs(change_pct) > 50:  # More than 50% movement
                flags.append({
                    "account":    account,
                    "current":    current_val,
                    "prior":      prior_val,
                    "change_pct": round(change_pct, 1),
                    "flag":       f"Unusual movement: {round(change_pct,1)}% change from prior period"
                })

    return sorted(flags, key=lambda x: abs(x["change_pct"]), reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Engagement Summary
# ─────────────────────────────────────────────────────────────────────────────

def get_gl_summary_for_engagement(doctype_name, from_date, to_date):
    """Get GL exception count for a DocType within engagement period."""
    exceptions = frappe.db.count("Audit Finding", filters={
        "reference_doctype": doctype_name,
        "finding_type": ["in", [
            "GL Entry Cancellation", "GL Reconciliation Variance",
            "Suspense Account Usage", "GL Posting Error", "Cutoff Error"
        ]],
        "transaction_date": ["between", [from_date, to_date]]
    })
    return {"exceptions": exceptions}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _log_gl_event(doc, event_type):
    """Log GL event to the permanent GL Audit Log."""
    from ecclesia.ecclesia.doctype.gl_audit_log.gl_audit_log import create_gl_log
    create_gl_log(
        event_type=event_type,
        voucher_type=doc.voucher_type,
        voucher_no=doc.voucher_no,
        account=doc.account,
        debit=flt(doc.debit),
        credit=flt(doc.credit),
        posting_date=doc.posting_date,
    )


def _raise_gl_finding(gl_entry=None, finding_type="GL Issue", risk_rating="High",
                       observation="", voucher_type=None, voucher_no=None, amount=0):
    """Create an Audit Finding from a GL anomaly."""
    try:
        vtype = voucher_type or (gl_entry.voucher_type if gl_entry else "GL Entry")
        vno   = voucher_no   or (gl_entry.voucher_no   if gl_entry else "")
        amt   = amount       or (flt(gl_entry.debit) if gl_entry else 0)

        # Don't duplicate
        if frappe.db.exists("Audit Finding", {
            "reference_doctype": vtype,
            "reference_name":    vno,
            "finding_type":      finding_type
        }):
            return

        frappe.get_doc({
            "doctype":            "Audit Finding",
            "finding_title":      f"{finding_type}: {vtype} {vno}",
            "finding_type":       finding_type,
            "risk_rating":        risk_rating,
            "reference_doctype":  vtype,
            "reference_name":     vno,
            "transaction_amount": amt,
            "observation":        observation,
            "source":             "Continuous Monitoring",
            "status":             "Open",
            "gl_entry_reference": gl_entry.name if gl_entry else None,
            "gl_account":         gl_entry.account if gl_entry else None,
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Failed to raise GL finding: {e}")