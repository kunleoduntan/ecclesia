# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/compliance/liability_engine_v2.py
"""
Compliance Liability Engine v2
═══════════════════════════════
Data-driven: reads Compliance Rule DocType for rate/frequency/base_doctype.
Generates Compliance Liability Ledger entries and logs to Compliance Event Log.

Public entry points
───────────────────
Batch (whitelisted, called by scheduler / dashboard):
    generate_vat_liability(company, period_label=None)
    generate_wht_liability(company, period_label=None)
    generate_payroll_liabilities(company, period_label=None)
    run_all_liability_generation(period_label=None, company=None)

Doc-event hooks (called by hooks.py doc_events, receive (doc, method)):
    generate_vat_liability_from_doc   -> Sales Invoice    on_submit
    log_purchase_invoice_wht          -> Purchase Invoice on_submit
    link_salary_slip_to_cll           -> Salary Slip      on_submit

hooks.py must therefore use:
    "Sales Invoice": {
        "on_submit": "ecclesia.api.compliance.liability_engine_v2.generate_vat_liability_from_doc"
    }

Safety net: Frappe calls a doc-event handler as handler(doc, method). If one of
the BATCH functions above is registered in hooks.py by mistake, it would receive
the document as `company` and the event name ("on_submit") as `period_label`,
and fail with "Invalid period_label format" — blocking every invoice. The batch
functions therefore detect a document as their first argument and hand it to the
matching doc-event function instead (see _doc_event_safe).

All functions are idempotent: re-running for the same period never adds a
source line that already exists on the ledger.

Doc-event functions run INSIDE the document's own transaction and must never
commit: a commit there would persist a half-submitted invoice (GL, stock) that
a later failure could not roll back. Only the batch/scheduler functions commit.
"""

import calendar
import functools
import inspect

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

# ── Statutory rates (fallbacks when no Compliance Rule / salary component) ────
VAT_RATE = 7.5
PENSION_EMPLOYEE_RATE = 0.08
PENSION_EMPLOYER_RATE = 0.10
NHF_RATE = 0.025
NSITF_RATE = 0.01

# Salary Component name used for PAYE on your payslips
PAYE_COMPONENT = "Tax"

# Which doc-event function handles which document (used by the safety net)
_DOC_EVENT_ROUTES = {
    "Sales Invoice": "generate_vat_liability_from_doc",
    "Purchase Invoice": "log_purchase_invoice_wht",
    "Salary Slip": "link_salary_slip_to_cll",
}


def _doc_event_safe(fn):
    """Let a batch function survive being registered as a doc_event by mistake.

    If the first argument is a document (not a company name), route it to the
    right doc-event function and return; documents with no route are ignored.
    Normal calls (scheduler, dashboard button, other code) are untouched.
    Also drops request fields the function does not declare (Frappe passes `cmd`)."""
    params = list(inspect.signature(fn).parameters)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        first = args[0] if args else None
        if first is not None and not isinstance(first, str) and hasattr(first, "doctype"):
            handler = globals().get(_DOC_EVENT_ROUTES.get(first.doctype, ""))
            method = args[1] if len(args) > 1 else kwargs.get("method")
            return handler(first, method) if handler else None
        kwargs = {k: v for k, v in kwargs.items() if k in params}
        return fn(*args, **kwargs)

    wrapper.fnargs = params  # Frappe reads this to decide which request fields to pass
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _period_label(date_str=None):
    """Return MM-YYYY for a date string (defaults to today)."""
    d = getdate(date_str or nowdate())
    return f"{d.month:02d}-{d.year:04d}"


def _period_bounds(period_label):
    """Return (start, end) ISO date strings for an MM-YYYY label."""
    try:
        month, year = (int(x) for x in period_label.split("-"))
        last_day = calendar.monthrange(year, month)[1]
    except Exception:
        frappe.throw(_("Invalid period_label format ({0}). Use MM-YYYY.").format(str(period_label)[:40]))
    return (
        f"{year:04d}-{month:02d}-01",
        f"{year:04d}-{month:02d}-{last_day:02d}",
    )


def _log_event(company, obligation_type, period_label, source_doctype, source_document,
               generated_ledger, liability_amount, status="Success", error=""):
    try:
        ev = frappe.new_doc("Compliance Event Log")
        ev.event_name = f"{obligation_type} | {period_label} | {source_doctype}"
        ev.event_type = (
            "Invoice" if "Invoice" in source_doctype
            else "Payroll" if "Salary" in source_doctype or "Payroll" in source_doctype
            else "Scheduler"
        )
        ev.source_doctype = source_doctype
        ev.source_document = source_document
        ev.obligation_type = obligation_type
        ev.period_label = period_label
        ev.company = company
        ev.generated_ledger = generated_ledger
        ev.liability_amount = flt(liability_amount)
        ev.status = status
        ev.error_log = error
        ev.processed_on = frappe.utils.now()
        ev.triggered_by = frappe.session.user
        ev.insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Compliance Event Log")


def _active_rule(company, obligation_type):
    """Name of the active Compliance Rule for company/obligation, or None."""
    return frappe.db.get_value(
        "Compliance Rule",
        {"obligation_type": obligation_type, "company": company, "active": 1},
        "name",
    )


def _get_deduction(salary_slip_name, component):
    """Read a specific deduction amount from a Salary Slip's deductions table."""
    return flt(frappe.db.get_value(
        "Salary Detail",
        {"parent": salary_slip_name, "salary_component": component,
         "parentfield": "deductions"},
        "amount",
    ) or 0)


def _paye_for_slip(salary_slip_name):
    """PAYE for a slip: the 'Tax' deduction row, else HRMS current_month_income_tax."""
    return (
        _get_deduction(salary_slip_name, PAYE_COMPONENT)
        or flt(frappe.db.get_value("Salary Slip", salary_slip_name, "current_month_income_tax"))
    )


def _existing_sources(cll):
    return {r.source_document for r in (cll.source_lines or [])}


def _add_line(cll, source_doctype, source_document, posting_date,
              gross_amount, liability_amount, rate_applied=None):
    """Append one source line to a CLL (does not save)."""
    row = {
        "source_doctype": source_doctype,
        "source_document": source_document,
        "posting_date": posting_date,
        "gross_amount": flt(gross_amount),
        "liability_amount": flt(liability_amount),
    }
    if rate_applied is not None:
        row["rate_applied"] = flt(rate_applied)
    cll.append("source_lines", row)


def _get_or_create_cll(company, obligation_type, period_label, rule=None, commit=True):
    """
    Fetch or create the CLL for company/obligation/period.
    Uses the Compliance Rule (passed in, or looked up) to get the due date.

    commit=True is for the batch/scheduler functions. The doc-event functions pass
    commit=False: they run inside the submitting document's transaction, and a
    commit here would persist a half-submitted invoice that cannot be rolled back.
    """
    existing = frappe.db.get_value(
        "Compliance Liability Ledger",
        {"company": company, "obligation_type": obligation_type, "period_label": period_label},
        "name",
    )
    if existing:
        return frappe.get_doc("Compliance Liability Ledger", existing)

    # Resolve rule (doc hooks don't pass one)
    if not rule:
        rule = _active_rule(company, obligation_type)

    # Resolve due date
    due_date = None
    rule_name = None
    if rule:
        try:
            rule_doc = frappe.get_doc("Compliance Rule", rule) if isinstance(rule, str) else rule
            rule_name = rule_doc.name
            due_date = rule_doc.get_due_date(period_label)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Compliance Rule due date")

    # Resolve period dates
    try:
        period_start, period_end = _period_bounds(period_label)
    except Exception:
        period_start = period_end = None

    # Resolve fiscal year
    fiscal_year = None
    if period_start and period_end:
        try:
            fiscal_year = frappe.db.get_value(
                "Fiscal Year",
                {"year_start_date": ["<=", period_start], "year_end_date": [">=", period_end]},
                "name",
            )
        except Exception:
            pass

    cll = frappe.new_doc("Compliance Liability Ledger")
    cll.company = company
    cll.obligation_type = obligation_type
    cll.period_label = period_label
    cll.fiscal_year = fiscal_year
    cll.period_start = period_start
    cll.period_end = period_end
    cll.due_date = due_date
    cll.total_liability = 0
    cll.generation_method = "Auto - Scheduler"
    cll.compliance_rule = rule_name
    cll.insert(ignore_permissions=True)
    if commit:
        frappe.db.commit()
    return cll


# ══════════════════════════════════════════════════════════════════════════════
#  VAT ENGINE (batch)
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
@_doc_event_safe
def generate_vat_liability(company, period_label=None):
    """Monthly batch: post VAT from all submitted Sales Invoices in the period."""
    period_label = period_label or _period_label()
    start, end = _period_bounds(period_label)
    rule = _active_rule(company, "VAT")

    # NB: literal % must be doubled (%%) because the query uses %s parameters.
    invoices = frappe.db.sql("""
        SELECT si.name, si.posting_date, si.net_total,
               COALESCE(SUM(st.tax_amount), 0) AS vat_amount
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Taxes and Charges` st
               ON st.parent = si.name
              AND (UPPER(st.account_head) LIKE '%%VAT%%' OR st.rate = 7.5)
        WHERE si.company = %s AND si.docstatus = 1
          AND si.posting_date BETWEEN %s AND %s
        GROUP BY si.name, si.posting_date, si.net_total
        HAVING vat_amount > 0
    """, (company, start, end), as_dict=True)

    if not invoices:
        return {"posted": 0, "total_vat": 0, "period": period_label}

    cll = _get_or_create_cll(company, "VAT", period_label, rule)
    existing = _existing_sources(cll)
    posted, total_vat = 0, 0.0

    for inv in invoices:
        if inv.name in existing:
            continue
        _add_line(cll, "Sales Invoice", inv.name, inv.posting_date,
                  inv.net_total, inv.vat_amount, VAT_RATE)
        total_vat += flt(inv.vat_amount)
        posted += 1

    if posted:
        cll.save(ignore_permissions=True)
        frappe.db.commit()
        _log_event(company, "VAT", period_label, "Sales Invoice",
                   f"{posted} invoices", cll.name, total_vat)

    return {"posted": posted, "total_vat": total_vat, "cll": cll.name, "period": period_label}


# ══════════════════════════════════════════════════════════════════════════════
#  WHT ENGINE (batch) — reads from Payments DocType
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
@_doc_event_safe
def generate_wht_liability(company, period_label=None):
    period_label = period_label or _period_label()
    start, end = _period_bounds(period_label)
    rule = _active_rule(company, "WHT")

    payments = frappe.db.sql("""
        SELECT name, transaction_date, wht_amount, net_amount, whtax_rate
        FROM `tabPayments`
        WHERE company = %s AND docstatus = 1 AND deduct_wht = 1
          AND wht_amount > 0
          AND transaction_date BETWEEN %s AND %s
    """, (company, start, end), as_dict=True)

    if not payments:
        return {"posted": 0, "total_wht": 0, "period": period_label}

    cll = _get_or_create_cll(company, "WHT", period_label, rule)
    existing = _existing_sources(cll)
    posted, total_wht = 0, 0.0

    for p in payments:
        if p.name in existing:
            continue
        _add_line(cll, "Payments", p.name, p.transaction_date,
                  p.net_amount, p.wht_amount, p.whtax_rate)
        total_wht += flt(p.wht_amount)
        posted += 1

    if posted:
        cll.save(ignore_permissions=True)
        frappe.db.commit()
        _log_event(company, "WHT", period_label, "Payments",
                   f"{posted} payment docs", cll.name, total_wht)

    return {"posted": posted, "total_wht": total_wht, "cll": cll.name, "period": period_label}


# ══════════════════════════════════════════════════════════════════════════════
#  PAYROLL LIABILITIES (batch) — PAYE, Pension, NHF, NSITF
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
@_doc_event_safe
def generate_payroll_liabilities(company, period_label=None):
    period_label = period_label or _period_label()
    start, end = _period_bounds(period_label)

    slips = frappe.db.sql("""
        SELECT name, gross_pay, start_date, end_date
        FROM `tabSalary Slip`
        WHERE company = %s AND docstatus = 1
          AND start_date >= %s AND end_date <= %s
    """, (company, start, end), as_dict=True)

    if not slips:
        return {"status": "No salary slips", "period": period_label}

    # Per-slip lines: ob -> list of (slip, gross, end_date, amount)
    lines = {"PAYE": [], "Pension": [], "NHF": []}
    total_gross = 0.0

    for s in slips:
        gross = flt(s.gross_pay)
        total_gross += gross

        paye = _paye_for_slip(s.name)
        if paye > 0:
            lines["PAYE"].append((s.name, gross, s.end_date, paye))

        pension_ee = _get_deduction(s.name, "Pension Contribution") or gross * PENSION_EMPLOYEE_RATE
        pension_er = gross * PENSION_EMPLOYER_RATE
        if pension_ee + pension_er > 0:
            lines["Pension"].append((s.name, gross, s.end_date, pension_ee + pension_er))

        nhf = _get_deduction(s.name, "NHF Contribution") or gross * NHF_RATE
        if nhf > 0:
            lines["NHF"].append((s.name, gross, s.end_date, nhf))

    results = {}

    # ── NSITF — 1% of gross payroll, one line per period (idempotent) ─────────
    if total_gross > 0:
        nsitf_amount = total_gross * NSITF_RATE
        cll_n = _get_or_create_cll(company, "NSITF", period_label, _active_rule(company, "NSITF"))
        src = f"Payroll-{period_label}"
        existing_n = _existing_sources(cll_n)

        if src in existing_n:
            # Refresh the amount in case slips were added since the last run
            for r in cll_n.source_lines:
                if r.source_document == src:
                    r.gross_amount = total_gross
                    r.liability_amount = nsitf_amount
            cll_n.save(ignore_permissions=True)
        else:
            _add_line(cll_n, "Payroll Entry", src, end, total_gross, nsitf_amount, NSITF_RATE * 100)
            cll_n.save(ignore_permissions=True)
            _log_event(company, "NSITF", period_label, "Payroll Entry",
                       "Monthly payroll", cll_n.name, nsitf_amount)
        results["NSITF"] = {"amount": nsitf_amount, "cll": cll_n.name}

    # ── PAYE / Pension / NHF — actual per-slip amounts ───────────────────────
    for ob, rows in lines.items():
        if not rows:
            continue
        cll = _get_or_create_cll(company, ob, period_label, _active_rule(company, ob))
        existing = _existing_sources(cll)
        added, added_amount = 0, 0.0

        for slip_name, gross, end_date, amount in rows:
            if slip_name in existing:
                continue
            _add_line(cll, "Salary Slip", slip_name, end_date, gross, amount)
            added += 1
            added_amount += amount

        if added:
            cll.save(ignore_permissions=True)
            _log_event(company, ob, period_label, "Salary Slip",
                       f"{added} slips", cll.name, added_amount)
        results[ob] = {"amount": sum(r[3] for r in rows), "added": added, "cll": cll.name}

    frappe.db.commit()
    return {"results": results, "period": period_label}


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER RUNNER (called by scheduler / dashboard button)
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
@_doc_event_safe
def run_all_liability_generation(period_label=None, company=None):
    period_label = period_label or _period_label()
    companies = [company] if company else frappe.db.get_all(
        "Company", filters={"is_group": 0}, pluck="name")
    results = {}

    steps = (
        ("vat", generate_vat_liability),
        ("wht", generate_wht_liability),
        ("payroll", generate_payroll_liabilities),
    )

    for co in companies:
        results[co] = {"status": "OK"}
        # Each step is isolated so one failure doesn't block the others
        for key, fn in steps:
            try:
                results[co][key] = fn(co, period_label)
            except Exception:
                frappe.db.rollback()
                tb = frappe.get_traceback()
                frappe.log_error(tb, f"Liability generation failed {co} [{key}]")
                results[co][key] = {"status": "Error"}
                results[co]["status"] = "Partial"

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  DOC-EVENT HOOKS — called directly by hooks.py doc_events
#  (run inside the document's transaction: they must never commit)
# ══════════════════════════════════════════════════════════════════════════════

def generate_vat_liability_from_doc(doc, method=None):
    """
    hooks.py doc_events -> Sales Invoice -> on_submit
    Posts VAT for a single submitted invoice. `doc` is the Sales Invoice.
    (Renamed from generate_vat_liability, which clashed with the batch function.)
    """
    if not doc or not doc.name:
        return
    try:
        pl = _period_label(doc.posting_date)

        vat_amount = 0.0
        for tax in (doc.taxes or []):
            ah = (tax.account_head or "").upper()
            if "VAT" in ah or flt(tax.rate) == VAT_RATE:
                vat_amount += flt(tax.tax_amount)
        if vat_amount <= 0:
            return

        cll = _get_or_create_cll(doc.company, "VAT", pl, commit=False)
        if doc.name not in _existing_sources(cll):
            _add_line(cll, "Sales Invoice", doc.name, doc.posting_date,
                      doc.net_total or doc.total, vat_amount, VAT_RATE)
            cll.save(ignore_permissions=True)
            frappe.db.set_value("Sales Invoice", doc.name,
                                "vat_cll_entry", cll.name, update_modified=False)
            _log_event(doc.company, "VAT", pl, "Sales Invoice", doc.name, cll.name, vat_amount)
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"VAT CLL generation failed for {doc.name}")


def log_purchase_invoice_wht(doc, method=None):
    """
    hooks.py doc_events -> Purchase Invoice -> on_submit
    Reads WHT deducted on a Purchase Invoice and posts it to the WHT CLL.
    """
    if not doc or not doc.name:
        return
    try:
        # Strategy 1: taxes table rows tagged as WHT
        wht_amount = 0.0
        for tax in (doc.taxes or []):
            ah = (tax.account_head or "").upper()
            if "WHT" in ah or "WITHHOLD" in ah:
                wht_amount += abs(flt(tax.tax_amount))

        # Strategy 2: custom field fallback
        if wht_amount <= 0:
            wht_amount = flt(doc.get("wht_amount") or 0)
        if wht_amount <= 0:
            return

        pl = _period_label(doc.posting_date)
        cll = _get_or_create_cll(doc.company, "WHT", pl, commit=False)
        if doc.name not in _existing_sources(cll):
            _add_line(cll, "Purchase Invoice", doc.name, doc.posting_date,
                      doc.net_total or doc.total, wht_amount)
            cll.save(ignore_permissions=True)
            frappe.db.set_value("Purchase Invoice", doc.name,
                                "wht_cll_entry", cll.name, update_modified=False)
            _log_event(doc.company, "WHT", pl, "Purchase Invoice", doc.name, cll.name, wht_amount)
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"WHT CLL logging failed for {doc.name}")


def link_salary_slip_to_cll(doc, method=None):
    """
    hooks.py doc_events -> Salary Slip -> on_submit
    Posts the slip to the PAYE / Pension / NHF CLLs and back-links them on the slip.
    """
    if not doc or not doc.name:
        return
    try:
        pl = _period_label(doc.end_date or doc.start_date)
        co = doc.company
        gross = flt(doc.gross_pay)
        back_links = {}

        pension_ee = _get_deduction(doc.name, "Pension Contribution") or gross * PENSION_EMPLOYEE_RATE
        pension_er = gross * PENSION_EMPLOYER_RATE

        items = (
            ("PAYE", _paye_for_slip(doc.name), "paye_cll_entry"),
            ("Pension", pension_ee + pension_er, "pension_cll_entry"),
            ("NHF", _get_deduction(doc.name, "NHF Contribution") or gross * NHF_RATE, "nhf_cll_entry"),
        )

        for ob, amount, link_field in items:
            if amount <= 0:
                continue
            cll = _get_or_create_cll(co, ob, pl, commit=False)
            if doc.name not in _existing_sources(cll):
                _add_line(cll, "Salary Slip", doc.name, doc.end_date, gross, amount)
                cll.save(ignore_permissions=True)
            back_links[link_field] = cll.name

        if back_links:
            frappe.db.set_value("Salary Slip", doc.name, back_links, update_modified=False)
        # no frappe.db.commit(): this runs inside the slip's own submit transaction

    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"Salary Slip CLL link failed for {doc.name}")