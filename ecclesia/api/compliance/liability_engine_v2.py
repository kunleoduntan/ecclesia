# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/api/compliance/liability_engine_v2.py
"""
Compliance Liability Engine v2
═══════════════════════════════
Data-driven: reads Compliance Rule DocType for rate/frequency/base_doctype.
Generates Compliance Liability Ledger entries and logs to Compliance Event Log.

Flow:
  1. load_active_rules(company, obligation_type)
  2. For each rule → compute liability from ERPNext source
  3. get_or_create_cll(company, obligation_type, period_label)
  4. cll.add_source_line(...)
  5. log to Compliance Event Log
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


# ── Helpers ──────────────────────────────────────────────────────────────────

def _period_label(date_str=None):
    """Return MM-YYYY for a date string (defaults to today)."""
    d = getdate(date_str or nowdate())
    return f"{d.month:02d}-{d.year:04d}"


def _log_event(company, obligation_type, period_label, source_doctype, source_document,
               generated_ledger, liability_amount, status="Success", error=""):
    try:
        ev = frappe.new_doc("Compliance Event Log")
        ev.event_name       = f"{obligation_type} | {period_label} | {source_doctype}"
        ev.event_type       = "Invoice" if "Invoice" in source_doctype else "Payroll" if "Salary" in source_doctype else "Scheduler"
        ev.source_doctype   = source_doctype
        ev.source_document  = source_document
        ev.obligation_type  = obligation_type
        ev.period_label     = period_label
        ev.company          = company
        ev.generated_ledger = generated_ledger
        ev.liability_amount = flt(liability_amount)
        ev.status           = status
        ev.error_log        = error
        ev.processed_on     = frappe.utils.now()
        ev.triggered_by     = frappe.session.user
        ev.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Event log write failed: {e}", "Compliance Event Log")


def _get_or_create_cll(company, obligation_type, period_label, rule=None):
    """
    Fetch or create the CLL for company/obligation/period.
    Uses Compliance Rule to get due_date if available.
    """
    existing = frappe.db.get_value(
        "Compliance Liability Ledger",
        {"company": company, "obligation_type": obligation_type, "period_label": period_label},
        "name"
    )
    if existing:
        return frappe.get_doc("Compliance Liability Ledger", existing)

    # Resolve due date
    due_date = None
    if rule:
        rule_doc = frappe.get_doc("Compliance Rule", rule) if isinstance(rule, str) else rule
        due_date = rule_doc.get_due_date(period_label)

    # Resolve period dates from period_label
    try:
        month, year = int(period_label.split('-')[0]), int(period_label.split('-')[1])
        import calendar
        last_day   = calendar.monthrange(year, month)[1]
        period_start = f"{year:04d}-{month:02d}-01"
        period_end   = f"{year:04d}-{month:02d}-{last_day:02d}"
    except Exception:
        period_start = period_end = None

    # Resolve fiscal year
    fiscal_year = None
    try:
        fiscal_year = frappe.db.get_value("Fiscal Year",
            {"year_start_date": ["<=", period_start], "year_end_date": [">=", period_end]}, "name")
    except Exception:
        pass

    cll = frappe.new_doc("Compliance Liability Ledger")
    cll.company          = company
    cll.obligation_type  = obligation_type
    cll.period_label     = period_label
    cll.fiscal_year      = fiscal_year
    cll.period_start     = period_start
    cll.period_end       = period_end
    cll.due_date         = due_date
    cll.total_liability  = 0
    cll.generation_method = "Auto - Scheduler"
    cll.compliance_rule  = rule if isinstance(rule, str) else (rule.name if rule else None)
    cll.insert(ignore_permissions=True)
    frappe.db.commit()
    return cll


# ══════════════════════════════════════════════════════════════════════════════
#  VAT ENGINE
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_vat_liability(company, period_label=None):
    period_label = period_label or _period_label()
    try:
        month, year = int(period_label.split('-')[0]), int(period_label.split('-')[1])
    except Exception:
        frappe.throw(_("Invalid period_label format. Use MM-YYYY."))

    start = f"{year:04d}-{month:02d}-01"
    import calendar
    end   = f"{year:04d}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}"

    rule = frappe.db.get_value("Compliance Rule",
        {"obligation_type":"VAT","company":company,"active":1}, "name")

    invoices = frappe.db.sql("""
        SELECT si.name, si.posting_date, si.net_total,
               COALESCE(SUM(st.tax_amount),0) AS vat_amount
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Taxes and Charges` st
               ON st.parent = si.name
              AND (UPPER(st.account_head) LIKE '%VAT%' OR st.rate = 7.5)
        WHERE si.company   = %s AND si.docstatus = 1
          AND si.posting_date BETWEEN %s AND %s
        GROUP BY si.name HAVING vat_amount > 0
    """, (company, start, end), as_dict=True)

    if not invoices:
        return {"posted": 0, "total_vat": 0, "period": period_label}

    cll = _get_or_create_cll(company, "VAT", period_label, rule)
    existing = {r.source_document for r in (cll.source_lines or [])}
    posted, total_vat = 0, 0

    for inv in invoices:
        if inv.name not in existing:
            cll.add_source_line("Sales Invoice", inv.name, inv.posting_date,
                                inv.net_total, inv.vat_amount, 7.5)
            total_vat += flt(inv.vat_amount)
            posted += 1

    cll.save(ignore_permissions=True)
    frappe.db.commit()

    _log_event(company, "VAT", period_label, "Sales Invoice", f"{posted} invoices",
               cll.name, total_vat)
    return {"posted": posted, "total_vat": total_vat, "cll": cll.name, "period": period_label}


# ══════════════════════════════════════════════════════════════════════════════
#  WHT ENGINE — reads from Payments DocType (our existing custom DocType)
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_wht_liability(company, period_label=None):
    period_label = period_label or _period_label()
    month, year = int(period_label.split('-')[0]), int(period_label.split('-')[1])
    import calendar
    start = f"{year:04d}-{month:02d}-01"
    end   = f"{year:04d}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}"

    rule = frappe.db.get_value("Compliance Rule",
        {"obligation_type":"WHT","company":company,"active":1}, "name")

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
    existing = {r.source_document for r in (cll.source_lines or [])}
    posted, total_wht = 0, 0

    for p in payments:
        if p.name not in existing:
            cll.add_source_line("Payments", p.name, p.transaction_date,
                                p.net_amount, p.wht_amount, p.whtax_rate)
            total_wht += flt(p.wht_amount)
            posted += 1

    cll.save(ignore_permissions=True)
    frappe.db.commit()
    _log_event(company, "WHT", period_label, "Payments", f"{posted} payment docs", cll.name, total_wht)
    return {"posted": posted, "total_wht": total_wht, "cll": cll.name, "period": period_label}


# ══════════════════════════════════════════════════════════════════════════════
#  PAYROLL LIABILITIES — PAYE, Pension, NHF, NSITF
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_payroll_liabilities(company, period_label=None):
    period_label = period_label or _period_label()
    month, year  = int(period_label.split('-')[0]), int(period_label.split('-')[1])
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start = f"{year:04d}-{month:02d}-01"
    end   = f"{year:04d}-{month:02d}-{last_day:02d}"

    slips = frappe.db.sql("""
        SELECT name, gross_pay, income_tax_deducted, start_date, end_date
        FROM `tabSalary Slip`
        WHERE company=%s AND docstatus=1
          AND start_date>=%s AND end_date<=%s
    """, (company, start, end), as_dict=True)

    if not slips:
        return {"status": "No salary slips", "period": period_label}

    totals = {
        "PAYE":   {"amount":0,"slips":[]},
        "Pension":{"amount":0,"slips":[]},
        "NHF":    {"amount":0,"slips":[]},
    }
    total_gross = 0.0

    for s in slips:
        gross = flt(s.gross_pay)
        total_gross += gross
        paye = flt(s.income_tax_deducted)
        if paye > 0:
            totals["PAYE"]["amount"] += paye
            totals["PAYE"]["slips"].append(s.name)
        pension_ee = _get_deduction(s.name, "Pension Contribution") or gross * 0.08
        pension_er = gross * 0.10
        totals["Pension"]["amount"] += pension_ee + pension_er
        totals["Pension"]["slips"].append(s.name)
        nhf = _get_deduction(s.name, "NHF Contribution") or gross * 0.025
        totals["NHF"]["amount"] += nhf
        totals["NHF"]["slips"].append(s.name)

    # NSITF — 1% of gross payroll
    if total_gross > 0:
        nsitf_amount = total_gross * 0.01
        rule_n = frappe.db.get_value("Compliance Rule", {"obligation_type":"NSITF","company":company,"active":1}, "name")
        cll_n  = _get_or_create_cll(company, "NSITF", period_label, rule_n)
        cll_n.append("source_lines", {
            "source_doctype":"Payroll Entry","source_document":f"Payroll-{period_label}",
            "posting_date":end,"gross_amount":total_gross,"liability_amount":nsitf_amount,"rate_applied":1.0
        })
        cll_n.save(ignore_permissions=True)
        _log_event(company,"NSITF",period_label,"Payroll Entry","Monthly payroll",cll_n.name,nsitf_amount)

    results = {}
    for ob, data in totals.items():
        if data["amount"] <= 0:
            continue
        rule_ref = frappe.db.get_value("Compliance Rule", {"obligation_type":ob,"company":company,"active":1}, "name")
        cll = _get_or_create_cll(company, ob, period_label, rule_ref)
        existing = {r.source_document for r in (cll.source_lines or [])}
        n_slips  = list(set(data["slips"]))
        amount_each = data["amount"] / len(n_slips) if n_slips else 0
        for sn in n_slips:
            if sn not in existing:
                slip_d = frappe.db.get_value("Salary Slip", sn, ["gross_pay","end_date"], as_dict=True)
                cll.append("source_lines", {
                    "source_doctype":"Salary Slip","source_document":sn,
                    "posting_date":slip_d.end_date,"gross_amount":flt(slip_d.gross_pay),
                    "liability_amount":amount_each
                })
        cll.save(ignore_permissions=True)
        _log_event(company,ob,period_label,"Salary Slip",f"{len(n_slips)} slips",cll.name,data["amount"])
        results[ob] = {"amount": data["amount"], "cll": cll.name}

    frappe.db.commit()
    return {"results": results, "period": period_label}


def _get_deduction(salary_slip, component):
    return flt(frappe.db.get_value("Salary Detail",
        {"parent": salary_slip, "salary_component": component}, "amount") or 0)


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER RUNNER (called by scheduler / dashboard button)
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_all_liability_generation(period_label=None, company=None):
    period_label = period_label or _period_label()
    companies    = [company] if company else frappe.db.get_all("Company", filters={"is_group":0}, pluck="name")
    results      = {}

    for co in companies:
        try:
            vat = generate_vat_liability(co, period_label)
            wht = generate_wht_liability(co, period_label)
            pay = generate_payroll_liabilities(co, period_label)
            results[co] = {"vat":vat,"wht":wht,"payroll":pay,"status":"OK"}
        except Exception as e:
            frappe.log_error(f"Liability generation failed {co}: {e}", "Compliance Liability Engine v2")
            results[co] = {"status":"Error","error":str(e)}

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  DOC-EVENT HOOKS — called directly by hooks.py doc_events
# ══════════════════════════════════════════════════════════════════════════════

def generate_vat_liability(doc, method=None):
    """
    hooks.py doc_events → Sales Invoice → on_submit
    Wraps generate_vat_liability() for a single invoice on submit.
    `doc` is the Sales Invoice document object passed by Frappe's hook runner.
    """
    if not doc or not doc.name:
        return
    try:
        pl = _period_label(doc.posting_date)
        # Sum VAT rows
        vat_amount = 0.0
        for tax in (doc.taxes or []):
            ah = (tax.account_head or "").upper()
            if "VAT" in ah or flt(tax.rate) == 7.5:
                vat_amount += flt(tax.tax_amount)
        if vat_amount <= 0:
            return

        cll = _get_or_create_cll(doc.company, "VAT", pl)
        existing = {r.source_document for r in (cll.source_lines or [])}
        if doc.name not in existing:
            cll.append("source_lines", {
                "source_doctype":  "Sales Invoice",
                "source_document": doc.name,
                "posting_date":    doc.posting_date,
                "gross_amount":    flt(doc.net_total or doc.total),
                "liability_amount": vat_amount,
                "rate_applied":    7.5,
            })
            cll.save(ignore_permissions=True)
            frappe.db.commit()
            # Back-link on invoice
            frappe.db.set_value("Sales Invoice", doc.name,
                                "vat_cll_entry", cll.name, update_modified=False)
            _log_event(doc.company, "VAT", pl, "Sales Invoice", doc.name,
                       cll.name, vat_amount)
    except Exception as e:
        frappe.log_error(f"VAT CLL generation failed for {doc.name}: {e}",
                         "Compliance Liability Engine")


def log_purchase_invoice_wht(doc, method=None):
    """
    hooks.py doc_events → Purchase Invoice → on_submit
    Reads WHT deducted on Purchase Invoice and posts to WHT CLL.
    Relies on ERPNext's Tax Withheld Vouchers or a custom wht_amount field.
    """
    if not doc or not doc.name:
        return
    try:
        # Strategy 1: read from taxes table rows tagged as WHT
        wht_amount = 0.0
        for tax in (doc.taxes or []):
            ah = (tax.account_head or "").upper()
            if "WHT" in ah or "WITHHOLD" in ah:
                wht_amount += flt(tax.tax_amount)

        # Strategy 2: fallback to custom field if present
        if wht_amount <= 0:
            wht_amount = flt(doc.get("wht_amount") or 0)

        if wht_amount <= 0:
            return

        pl  = _period_label(doc.posting_date)
        cll = _get_or_create_cll(doc.company, "WHT", pl)
        existing = {r.source_document for r in (cll.source_lines or [])}
        if doc.name not in existing:
            cll.append("source_lines", {
                "source_doctype":  "Purchase Invoice",
                "source_document": doc.name,
                "posting_date":    doc.posting_date,
                "gross_amount":    flt(doc.net_total or doc.total),
                "liability_amount": wht_amount,
            })
            cll.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.db.set_value("Purchase Invoice", doc.name,
                                "wht_cll_entry", cll.name, update_modified=False)
            _log_event(doc.company, "WHT", pl, "Purchase Invoice", doc.name,
                       cll.name, wht_amount)
    except Exception as e:
        frappe.log_error(f"WHT CLL logging failed for {doc.name}: {e}",
                         "Compliance Liability Engine")


def link_salary_slip_to_cll(doc, method=None):
    """
    hooks.py doc_events → Salary Slip → on_submit
    Back-links the salary slip to the PAYE / Pension / NHF CLL entries
    for the slip's payroll period so each slip is traceable from the ledger.
    """
    if not doc or not doc.name:
        return
    try:
        pl   = _period_label(doc.end_date or doc.start_date)
        co   = doc.company
        back_links = {}

        # PAYE
        paye = flt(doc.income_tax_deducted)
        if paye > 0:
            cll = _get_or_create_cll(co, "PAYE", pl)
            existing = {r.source_document for r in (cll.source_lines or [])}
            if doc.name not in existing:
                cll.append("source_lines", {
                    "source_doctype":  "Salary Slip",
                    "source_document": doc.name,
                    "posting_date":    doc.end_date,
                    "gross_amount":    flt(doc.gross_pay),
                    "liability_amount": paye,
                })
                cll.save(ignore_permissions=True)
            back_links["paye_cll_entry"] = cll.name

        # Pension — compute if not in deductions
        gross = flt(doc.gross_pay)
        pension_ee = _get_deduction(doc.name, "Pension Contribution") or (gross * 0.08)
        pension_er = gross * 0.10
        pension_total = pension_ee + pension_er
        if pension_total > 0:
            cll = _get_or_create_cll(co, "Pension", pl)
            existing = {r.source_document for r in (cll.source_lines or [])}
            if doc.name not in existing:
                cll.append("source_lines", {
                    "source_doctype":  "Salary Slip",
                    "source_document": doc.name,
                    "posting_date":    doc.end_date,
                    "gross_amount":    gross,
                    "liability_amount": pension_total,
                })
                cll.save(ignore_permissions=True)
            back_links["pension_cll_entry"] = cll.name

        # NHF
        nhf = _get_deduction(doc.name, "NHF Contribution") or (gross * 0.025)
        if nhf > 0:
            cll = _get_or_create_cll(co, "NHF", pl)
            existing = {r.source_document for r in (cll.source_lines or [])}
            if doc.name not in existing:
                cll.append("source_lines", {
                    "source_doctype":  "Salary Slip",
                    "source_document": doc.name,
                    "posting_date":    doc.end_date,
                    "gross_amount":    gross,
                    "liability_amount": nhf,
                })
                cll.save(ignore_permissions=True)
            back_links["nhf_cll_entry"] = cll.name

        # Write back-links to the Salary Slip in one call
        if back_links:
            frappe.db.set_value("Salary Slip", doc.name, back_links,
                                update_modified=False)

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Salary Slip CLL link failed for {doc.name}: {e}",
                         "Compliance Liability Engine")


def _get_deduction(salary_slip_name, component):
    """Read a specific deduction amount from Salary Slip deductions table."""
    return flt(frappe.db.get_value(
        "Salary Detail",
        {"parent": salary_slip_name, "salary_component": component},
        "amount"
    ) or 0)