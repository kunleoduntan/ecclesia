"""
GL Analytical Review — ISA 520 Analytical Procedures
======================================================
Provides comparative analysis of GL account balances across periods.
Identifies unusual movements, new accounts, dormant accounts,
and period-end clustering — all standard ISA 520 procedures.
"""

import frappe
from frappe.utils import flt, getdate, add_months, get_first_day, get_last_day


@frappe.whitelist()
def get_analytical_review(from_date, to_date, prior_from_date, prior_to_date,
                           threshold_pct=50, min_amount=10000):
    """
    Run full ISA 520 analytical review comparing current vs prior period GL balances.
    Returns flagged accounts, summary stats, and account-level data.
    """
    threshold_pct = flt(threshold_pct)
    min_amount    = flt(min_amount)

    current = _get_account_movements(from_date, to_date)
    prior   = _get_account_movements(prior_from_date, prior_to_date)

    prior_map = {r["account"]: r for r in prior}
    flags = []
    all_accounts = []

    for row in current:
        account    = row["account"]
        current_val= flt(row["net_movement"])
        root_type  = row.get("root_type", "")
        acc_type   = row.get("account_type", "")
        prior_row  = prior_map.get(account)
        prior_val  = flt(prior_row["net_movement"]) if prior_row else 0

        change_pct = 0
        if prior_val != 0:
            change_pct = ((current_val - prior_val) / abs(prior_val)) * 100
        elif abs(current_val) > 0:
            change_pct = 100  # New account

        flag_reasons = []

        # New account with significant activity
        if not prior_row and abs(current_val) >= min_amount:
            flag_reasons.append("New account with significant activity")

        # Large movement vs prior period
        if abs(change_pct) >= threshold_pct and abs(current_val) >= min_amount:
            direction = "increase" if change_pct > 0 else "decrease"
            flag_reasons.append(f"{abs(round(change_pct,1))}% {direction} vs prior period")

        # Unexpected direction (revenue down while assets up, etc.)
        if root_type == "Income" and current_val < 0 and prior_val > 0:
            flag_reasons.append("Revenue account shows debit balance — classification risk")
        if root_type == "Expense" and current_val < 0:
            flag_reasons.append("Expense account shows credit balance — possible reversal/write-back")

        entry = {
            "account":       account,
            "account_type":  acc_type,
            "root_type":     root_type,
            "current":       current_val,
            "prior":         prior_val,
            "change":        current_val - prior_val,
            "change_pct":    round(change_pct, 1),
            "flagged":       len(flag_reasons) > 0,
            "flag_reasons":  "; ".join(flag_reasons),
        }
        all_accounts.append(entry)
        if flag_reasons:
            flags.append(entry)

    # Suspense accounts
    suspense = _get_suspense_usage(from_date, to_date)

    # Period-end clustering
    period_end = _get_period_end_clustering(from_date, to_date)

    # Journal entry summary
    je_summary = _get_journal_entry_summary(from_date, to_date)

    return {
        "flagged_accounts":   sorted(flags, key=lambda x: abs(x["change_pct"]), reverse=True),
        "all_accounts":       sorted(all_accounts, key=lambda x: abs(x["change"]), reverse=True)[:50],
        "suspense_usage":     suspense,
        "period_end_entries": period_end,
        "je_summary":         je_summary,
        "summary": {
            "total_accounts_current": len(current),
            "total_accounts_prior":   len(prior),
            "flagged_count":          len(flags),
            "from_date":              from_date,
            "to_date":                to_date,
            "prior_from":             prior_from_date,
            "prior_to":               prior_to_date,
        }
    }


def _get_account_movements(from_date, to_date):
    return frappe.db.sql("""
        SELECT
            gl.account,
            acc.account_type,
            acc.root_type,
            SUM(gl.debit - gl.credit) as net_movement
        FROM `tabGL Entry` gl
        LEFT JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND gl.is_cancelled = 0
        GROUP BY gl.account, acc.account_type, acc.root_type
        HAVING ABS(SUM(gl.debit - gl.credit)) > 0
        ORDER BY ABS(SUM(gl.debit - gl.credit)) DESC
        LIMIT 500
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)


def _get_suspense_usage(from_date, to_date):
    return frappe.db.sql("""
        SELECT gl.account, gl.voucher_type, gl.voucher_no,
               gl.posting_date, (gl.debit + gl.credit) as amount,
               gl.party, gl.remarks
        FROM `tabGL Entry` gl
        WHERE gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND gl.is_cancelled = 0
        AND (LOWER(gl.account) LIKE '%%suspense%%'
             OR LOWER(gl.account) LIKE '%%clearing%%'
             OR LOWER(gl.account) LIKE '%%holding%%'
             OR LOWER(gl.account) LIKE '%%interim%%')
        ORDER BY amount DESC
        LIMIT 50
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)


def _get_period_end_clustering(from_date, to_date):
    """Detect transactions in last 3 days of each month — window dressing risk."""
    return frappe.db.sql("""
        SELECT
            DATE_FORMAT(posting_date, '%%Y-%%m') as month,
            SUM(CASE WHEN DAY(posting_date) >= 28 THEN 1 ELSE 0 END) as period_end_count,
            COUNT(*) as total_count,
            SUM(CASE WHEN DAY(posting_date) >= 28 THEN debit + credit ELSE 0 END) as period_end_amount
        FROM `tabGL Entry`
        WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND is_cancelled = 0
        GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
        ORDER BY month
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)


def _get_journal_entry_summary(from_date, to_date):
    """Journal entry analysis for the period."""
    result = frappe.db.sql("""
        SELECT
            COUNT(*) as total_jes,
            SUM(total_debit) as total_amount,
            SUM(CASE WHEN user_remark IS NULL OR user_remark = '' THEN 1 ELSE 0 END) as no_narration,
            SUM(CASE WHEN total_debit >= 1000 AND MOD(total_debit, 1000) = 0 THEN 1 ELSE 0 END) as round_amounts
        FROM `tabJournal Entry`
        WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND docstatus = 1
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

    return result[0] if result else {}