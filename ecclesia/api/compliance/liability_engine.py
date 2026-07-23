# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/api/compliance/liability_engine.py
"""
Compliance Liability Engine
═══════════════════════════
Reads ERPNext source documents and posts entries into the
Compliance Liability Ledger (CLL) — one per obligation-type per month.

Called by:
  • Scheduled job (daily) via hooks.py → scheduler_events
  • hooks.py → doc_events on Sales Invoice, Purchase Invoice, Salary Slip on_submit
  • Manual trigger from the ComplianceHQ dashboard

Architecture:
  Transactions (ERPNext) → Liability Engine → CLL → Payments DocType → Allocation Engine → CLL updated
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days, get_first_day, get_last_day
from datetime import datetime


# ── Constants ────────────────────────────────────────────────────────────────

# Default rates when not found in Tax Settings or item tax templates
DEFAULT_VAT_RATE   = 0.075   # 7.5%
DEFAULT_WHT_RATES  = {
    # Nature of payment → WHT rate under Nigeria Tax Act 2025/2026
    "Dividend":           0.10,
    "Interest":           0.10,
    "Rent":               0.10,
    "Royalties":          0.10,
    "Commission":         0.10,
    "Management Fees":    0.10,
    "Director Fees":      0.10,
    "Consultancy":        0.10,
    "Technical Services": 0.10,
    "Construction":       0.025,  # 2.5%
    "Contract":           0.05,   # 5%
    "Default":            0.05,
}
PENSION_EE_RATE    = 0.08   # 8% employee
PENSION_ER_RATE    = 0.10   # 10% employer
NHF_EE_RATE        = 0.025  # 2.5%
NSITF_ER_RATE      = 0.01   # 1%
ITF_RATE           = 0.01   # 1% of annual payroll


# ── Entry point: get or create a CLL record ─────────────────────────────────

def get_or_create_cll(company, obligation_type, fiscal_month, due_date=None,
                      generation_method="Auto - Invoice"):
    """
    Fetch existing CLL for the company/obligation/month or create a new one.
    Returns the CLL document (unsaved or saved).
    """
    existing = frappe.db.get_value(
        "Compliance Liability Ledger",
        {"company": company, "obligation_type": obligation_type, "fiscal_month": fiscal_month},
        "name"
    )
    if existing:
        return frappe.get_doc("Compliance Liability Ledger", existing)

    # Compute due date from Compliance Requirement if not provided
    if not due_date:
        due_date = _compute_due_date(obligation_type, fiscal_month)

    period_start, period_end = _get_period_dates(fiscal_month)

    cll = frappe.new_doc("Compliance Liability Ledger")
    cll.company           = company
    cll.obligation_type   = obligation_type
    cll.fiscal_month      = fiscal_month
    cll.period_start      = period_start
    cll.period_end        = period_end
    cll.due_date          = due_date
    cll.amount_calculated = 0
    cll.generation_method = generation_method
    cll.insert(ignore_permissions=True)
    frappe.db.commit()
    return cll


def _compute_due_date(obligation_type, fiscal_month):
    """
    Default due dates per Nigerian regulation:
    VAT / WHT / PAYE → 21st of following month
    Pension           → 7th of following month
    NHF / NSITF       → 1st of following month
    ITF               → 1 April each year
    CIT               → 6 months after fiscal year end
    """
    year, month = map(int, fiscal_month.split("-"))
    if obligation_type in ("VAT", "WHT", "PAYE"):
        # 21st of following month
        next_month = month + 1 if month < 12 else 1
        next_year  = year if month < 12 else year + 1
        return f"{next_year:04d}-{next_month:02d}-21"
    elif obligation_type == "Pension":
        next_month = month + 1 if month < 12 else 1
        next_year  = year if month < 12 else year + 1
        return f"{next_year:04d}-{next_month:02d}-07"
    elif obligation_type in ("NHF", "NSITF"):
        next_month = month + 1 if month < 12 else 1
        next_year  = year if month < 12 else year + 1
        return f"{next_year:04d}-{next_month:02d}-01"
    elif obligation_type == "ITF":
        return f"{year + 1:04d}-04-01"
    else:
        return f"{year:04d}-{month:02d}-30"


def _get_period_dates(fiscal_month):
    """Return first and last day of a YYYY-MM period."""
    year, month = map(int, fiscal_month.split("-"))
    start = f"{year:04d}-{month:02d}-01"
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    end = f"{year:04d}-{month:02d}-{last_day:02d}"
    return start, end


def _fiscal_month_of(date_str):
    """Return YYYY-MM for a date string."""
    d = getdate(date_str)
    return f"{d.year:04d}-{d.month:02d}"


# ══════════════════════════════════════════════════════════════════════════════
#  VAT LIABILITY ENGINE
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def post_vat_liability_from_invoice(invoice_name, invoice_type="Sales Invoice"):
    """
    Called on_submit of Sales Invoice / Purchase Invoice.
    Reads VAT tax rows and posts/updates the VAT CLL entry for that fiscal month.
    """
    doc = frappe.get_doc(invoice_type, invoice_name)
    company      = doc.company
    fiscal_month = _fiscal_month_of(doc.posting_date)

    # Sum VAT from taxes table (account heads containing 'VAT' or rate = 7.5%)
    vat_amount = 0.0
    for tax in (doc.taxes or []):
        account_head = (tax.account_head or "").upper()
        if "VAT" in account_head or flt(tax.rate) == 7.5:
            vat_amount += flt(tax.tax_amount)

    if vat_amount <= 0:
        return  # No VAT on this invoice

    cll = get_or_create_cll(company, "VAT", fiscal_month)
    cll.add_source_line(
        source_doctype   = invoice_type,
        source_name      = invoice_name,
        posting_date     = doc.posting_date,
        gross_base       = flt(doc.net_total or doc.total),
        liability_amount = vat_amount,
        rate_applied     = 7.5,
    )
    cll.save(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist()
def run_vat_generation(company, fiscal_month):
    """
    Full re-scan: aggregate all Sales Invoice VAT for a fiscal month.
    Safe to run multiple times (deduplicates by source_name).
    """
    year, month = map(int, fiscal_month.split("-"))
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date   = f"{year:04d}-{month:02d}-{last_day:02d}"

    invoices = frappe.db.sql("""
        SELECT si.name, si.posting_date, si.net_total, si.total,
               COALESCE(SUM(st.tax_amount), 0) AS vat_amount
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Taxes and Charges` st
               ON st.parent = si.name
              AND (st.account_head LIKE '%VAT%' OR st.rate = 7.5)
        WHERE si.company    = %s
          AND si.docstatus  = 1
          AND si.posting_date BETWEEN %s AND %s
        GROUP BY si.name
        HAVING vat_amount > 0
    """, (company, start_date, end_date), as_dict=True)

    if not invoices:
        return {"message": f"No VAT invoices found for {company} in {fiscal_month}"}

    cll = get_or_create_cll(company, "VAT", fiscal_month)
    existing_sources = {row.source_name for row in (cll.source_lines or [])}
    added = 0

    for inv in invoices:
        if inv.name not in existing_sources:
            cll.append("source_lines", {
                "source_doctype":   "Sales Invoice",
                "source_name":      inv.name,
                "posting_date":     inv.posting_date,
                "gross_base":       flt(inv.net_total or inv.total),
                "liability_amount": flt(inv.vat_amount),
                "rate_applied":     7.5,
            })
            cll.amount_calculated = flt(cll.amount_calculated) + flt(inv.vat_amount)
            added += 1

    cll.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"Posted VAT for {fiscal_month}: {added} new invoices. Total: {cll.amount_calculated}"}


# ══════════════════════════════════════════════════════════════════════════════
#  WHT LIABILITY ENGINE
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_wht_generation(company, fiscal_month):
    """
    Aggregate WHT from Purchase Invoices and Payments for a fiscal month.
    Reads the wht_amount field on the Payments DocType.
    """
    year, month = map(int, fiscal_month.split("-"))
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date   = f"{year:04d}-{month:02d}-{last_day:02d}"

    # From Payments DocType (has wht_amount field)
    payments = frappe.db.sql("""
        SELECT name, transaction_date, net_amount, wht_amount, whtax_rate
        FROM `tabPayments`
        WHERE company   = %s
          AND docstatus = 1
          AND deduct_wht = 1
          AND wht_amount > 0
          AND transaction_date BETWEEN %s AND %s
    """, (company, start_date, end_date), as_dict=True)

    if not payments:
        return {"message": f"No WHT found for {company} in {fiscal_month}"}

    cll = get_or_create_cll(company, "WHT", fiscal_month)
    existing_sources = {row.source_name for row in (cll.source_lines or [])}
    added = 0

    for pay in payments:
        if pay.name not in existing_sources:
            cll.append("source_lines", {
                "source_doctype":   "Payments",
                "source_name":      pay.name,
                "posting_date":     pay.transaction_date,
                "gross_base":       flt(pay.net_amount),
                "liability_amount": flt(pay.wht_amount),
                "rate_applied":     flt(pay.whtax_rate),
            })
            cll.amount_calculated = flt(cll.amount_calculated) + flt(pay.wht_amount)
            added += 1

    cll.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"Posted WHT for {fiscal_month}: {added} payments. Total: {cll.amount_calculated}"}


# ══════════════════════════════════════════════════════════════════════════════
#  PAYROLL LIABILITIES ENGINE (PAYE, Pension, NHF, NSITF, ITF)
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_payroll_liabilities(company, fiscal_month):
    """
    Read ERPNext Salary Slips for the period and post:
    PAYE / Pension (EE+ER) / NHF / NSITF / ITF into separate CLL entries.

    Reads from:
      - Salary Slip: income_tax_deducted, gross_pay, net_pay
      - Employee's deductions for pension, NHF from salary_details child table
      - statutory_deduction_item child table (Pension, NHF etc.)
    """
    year, month = map(int, fiscal_month.split("-"))
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date   = f"{year:04d}-{month:02d}-{last_day:02d}"

    slips = frappe.db.sql("""
        SELECT name, employee, employee_name, gross_pay, net_pay,
               total_deduction, income_tax_deducted, start_date, end_date
        FROM `tabSalary Slip`
        WHERE company    = %s
          AND docstatus  = 1
          AND start_date >= %s
          AND end_date   <= %s
    """, (company, start_date, end_date), as_dict=True)

    if not slips:
        return {"message": f"No salary slips for {company} in {fiscal_month}"}

    # Aggregates
    totals = {
        "PAYE":    {"amount": 0, "slips": []},
        "Pension": {"amount": 0, "slips": []},
        "NHF":     {"amount": 0, "slips": []},
        "NSITF":   {"amount": 0, "slips": []},
    }
    total_gross = 0.0

    for slip in slips:
        gross = flt(slip.gross_pay)
        total_gross += gross

        # PAYE (income_tax_deducted field on Salary Slip)
        paye = flt(slip.income_tax_deducted)
        if paye > 0:
            totals["PAYE"]["amount"] += paye
            totals["PAYE"]["slips"].append(slip.name)

        # Pension — read from deductions child table
        pension_ee = _get_deduction(slip.name, "Pension Contribution") or (gross * PENSION_EE_RATE)
        pension_er = gross * PENSION_ER_RATE
        pension_total = pension_ee + pension_er
        totals["Pension"]["amount"] += pension_total
        totals["Pension"]["slips"].append(slip.name)

        # NHF
        nhf = _get_deduction(slip.name, "NHF Contribution") or (gross * NHF_EE_RATE)
        totals["NHF"]["amount"] += nhf
        totals["NHF"]["slips"].append(slip.name)

    # NSITF — 1% of gross payroll (employer only)
    totals["NSITF"]["amount"] = total_gross * NSITF_ER_RATE

    results = {}
    for obligation_type, data in totals.items():
        if data["amount"] <= 0:
            continue
        cll = get_or_create_cll(company, obligation_type, fiscal_month,
                                 generation_method="Auto - Payroll")
        existing = {row.source_name for row in (cll.source_lines or [])}
        for slip_name in set(data["slips"]):
            if slip_name not in existing:
                slip_doc = frappe.db.get_value("Salary Slip", slip_name, ["gross_pay","end_date"], as_dict=True)
                cll.append("source_lines", {
                    "source_doctype":   "Salary Slip",
                    "source_name":      slip_name,
                    "posting_date":     slip_doc.end_date,
                    "gross_base":       flt(slip_doc.gross_pay),
                    "liability_amount": data["amount"] / len(set(data["slips"])),
                })
        # Reset and recompute total from source lines
        cll.amount_calculated = sum(flt(r.liability_amount) for r in cll.source_lines)
        cll.save(ignore_permissions=True)
        results[obligation_type] = cll.amount_calculated

    frappe.db.commit()
    return {"message": f"Payroll liabilities posted for {fiscal_month}", "totals": results}


def _get_deduction(salary_slip_name, deduction_type):
    """Read a specific deduction amount from Salary Slip deductions table."""
    result = frappe.db.get_value(
        "Salary Detail",
        {"parent": salary_slip_name, "salary_component": deduction_type},
        "amount"
    )
    return flt(result) if result else 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  ITF ANNUAL LEVY ENGINE
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_itf_generation(company, fiscal_year):
    """
    ITF = 1% of annual payroll for qualifying companies.
    Called once per year. Creates a single CLL entry for the fiscal year.
    """
    year = int(str(fiscal_year)[:4])
    fiscal_month = f"{year:04d}-04"  # ITF due April

    annual_payroll = frappe.db.sql("""
        SELECT COALESCE(SUM(gross_pay), 0) AS total
        FROM `tabSalary Slip`
        WHERE company   = %s
          AND docstatus = 1
          AND YEAR(start_date) = %s
    """, (company, year), as_dict=True)[0].total

    itf_amount = flt(annual_payroll) * ITF_RATE
    if itf_amount <= 0:
        return {"message": "No payroll found for ITF calculation"}

    cll = get_or_create_cll(company, "ITF", fiscal_month,
                             due_date=f"{year + 1:04d}-04-01",
                             generation_method="Auto - Scheduler")
    cll.amount_calculated = itf_amount
    cll.remarks = f"ITF 1% of annual payroll ₦{annual_payroll:,.2f} for FY {fiscal_year}"
    cll.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"ITF liability ₦{itf_amount:,.2f} posted for {fiscal_month}"}


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER RUNNER — called by scheduler
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_all_liability_generation(fiscal_month=None):
    """
    Master runner: posts all obligation liabilities for the given fiscal month.
    Called daily by scheduled job; defaults to current month.
    """
    if not fiscal_month:
        d = getdate(nowdate())
        fiscal_month = f"{d.year:04d}-{d.month:02d}"

    companies = frappe.db.get_all("Company", filters={"is_group": 0}, pluck="name")
    results = {}

    for company in companies:
        try:
            vat  = run_vat_generation(company, fiscal_month)
            wht  = run_wht_generation(company, fiscal_month)
            pay  = run_payroll_liabilities(company, fiscal_month)
            results[company] = {"vat": vat, "wht": wht, "payroll": pay}
        except Exception as e:
            frappe.log_error(f"Liability generation failed for {company}: {e}",
                             "Compliance Liability Engine")
            results[company] = {"error": str(e)}

    return results