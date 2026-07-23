# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/api/compliance/compliance_dashboard_api.py
"""
ComplianceHQ Dashboard API
All whitelisted methods called from the compliance_hq.js page.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate, date_diff, add_days
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER DASHBOARD SUMMARY — called on page load
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_dashboard_summary(company, fiscal_month=None):
    """
    Returns the full KPI summary for all tabs of ComplianceHQ.
    One API call replaces 12 separate calls.
    """
    if not fiscal_month:
        d = getdate(nowdate())
        fiscal_month = f"{d.year:04d}-{d.month:02d}"

    return {
        "fiscal_month":  fiscal_month,
        "tax":           _get_tax_summary(company, fiscal_month),
        "statutory":     _get_statutory_summary(company, fiscal_month),
        "licenses":      _get_license_summary(company),
        "filings":       _get_filings_summary(company),
        "audit":         _get_audit_summary(company),
        "risk":          _get_risk_summary(company),
        "incidents":     _get_incidents_summary(company),
        "calendar":      _get_calendar_upcoming(company),
        "compliance_score": _compute_score(company),
    }


# ── Tax Widget (VAT, WHT, PAYE, CIT) ────────────────────────────────────────

def _get_tax_summary(company, fiscal_month):
    obligations = ["VAT", "WHT", "PAYE", "CIT"]
    result = {}
    for ob in obligations:
        cll = frappe.db.get_value(
            "Compliance Liability Ledger",
            {"company": company, "obligation_type": ob, "fiscal_month": fiscal_month},
            ["amount_calculated", "amount_paid", "balance", "status", "due_date", "name"],
            as_dict=True
        )
        if cll:
            result[ob] = {
                "liability": flt(cll.amount_calculated),
                "paid":      flt(cll.amount_paid),
                "balance":   flt(cll.balance),
                "status":    cll.status,
                "due_date":  cll.due_date,
                "cll_name":  cll.name,
                "days_until_due": date_diff(cll.due_date, nowdate()) if cll.due_date else None,
            }
        else:
            result[ob] = {"status": "Not Generated", "liability": 0, "paid": 0, "balance": 0}

    # 12-month trend
    result["trend"] = _get_cll_trend(company, "VAT", 12)
    return result


# ── Statutory Widget (Pension, NHF, NSITF, ITF) ─────────────────────────────

def _get_statutory_summary(company, fiscal_month):
    obligations = ["Pension", "NHF", "NSITF", "ITF"]
    result = {}
    for ob in obligations:
        cll = frappe.db.get_value(
            "Compliance Liability Ledger",
            {"company": company, "obligation_type": ob, "fiscal_month": fiscal_month},
            ["amount_calculated", "amount_paid", "balance", "status", "due_date", "name"],
            as_dict=True
        )
        if cll:
            result[ob] = {
                "liability": flt(cll.amount_calculated),
                "paid":      flt(cll.amount_paid),
                "balance":   flt(cll.balance),
                "status":    cll.status,
                "due_date":  cll.due_date,
                "cll_name":  cll.name,
            }
        else:
            result[ob] = {"status": "Not Generated", "liability": 0, "paid": 0, "balance": 0}
    return result


# ── License Widget ────────────────────────────────────────────────────────────

def _get_license_summary(company):
    all_lics = frappe.db.get_all(
        "License and Permit",
        filters={"company": company},
        fields=["name", "license_name", "license_type", "status", "expiry_date",
                "days_to_expiry", "responsible_officer", "renewal_cost", "authority"]
    )
    expired   = [l for l in all_lics if l.status == "Expired"]
    expiring  = [l for l in all_lics if l.status == "Expiring Soon"]
    valid     = [l for l in all_lics if l.status == "Valid"]

    return {
        "total":       len(all_lics),
        "valid":       len(valid),
        "expiring":    len(expiring),
        "expired":     len(expired),
        "expired_list":  expired[:10],
        "expiring_list": sorted(expiring, key=lambda x: x.days_to_expiry or 999)[:10],
        "all":           sorted(all_lics, key=lambda x: x.expiry_date or "9999-12-31")[:30],
    }


# ── Filings Widget ────────────────────────────────────────────────────────────

def _get_filings_summary(company):
    total = frappe.db.count("Compliance Filing", {"company": company, "docstatus": 1})
    accepted = frappe.db.count("Compliance Filing", {"company": company, "docstatus": 1, "status": "Accepted"})
    rejected = frappe.db.count("Compliance Filing", {"company": company, "docstatus": 1, "status": "Rejected"})
    recent   = frappe.db.get_all(
        "Compliance Filing",
        filters={"company": company, "docstatus": 1},
        fields=["name", "filing_title", "obligation_type", "fiscal_month",
                "filing_date", "status", "liability_amount", "amount_paid"],
        order_by="filing_date desc",
        limit=10
    )
    return {"total": total, "accepted": accepted, "rejected": rejected, "recent": recent}


# ── Audit Widget ──────────────────────────────────────────────────────────────

def _get_audit_summary(company):
    open_findings = frappe.db.sql("""
        SELECT COUNT(*) as cnt FROM `tabCompliance Audit Finding` caf
        JOIN `tabCompliance Audit` ca ON ca.name = caf.parent
        WHERE ca.company = %s AND caf.status IN ('Open', 'In Progress')
    """, (company,))[0][0]

    critical_findings = frappe.db.sql("""
        SELECT COUNT(*) as cnt FROM `tabCompliance Audit Finding` caf
        JOIN `tabCompliance Audit` ca ON ca.name = caf.parent
        WHERE ca.company = %s AND caf.risk_rating = 'Critical' AND caf.status = 'Open'
    """, (company,))[0][0]

    recent_audits = frappe.db.get_all(
        "Compliance Audit",
        filters={"company": company, "docstatus": 1},
        fields=["name", "audit_title", "audit_type", "status", "overall_rating",
                "actual_date", "critical_findings", "open_findings"],
        order_by="actual_date desc",
        limit=5
    )

    return {
        "open_findings": open_findings,
        "critical_findings": critical_findings,
        "recent_audits": recent_audits,
    }


# ── Risk Widget ───────────────────────────────────────────────────────────────

def _get_risk_summary(company):
    latest_register = frappe.db.get_value(
        "Compliance Risk Register",
        {"company": company, "status": "Active", "docstatus": 1},
        ["name", "critical_count", "high_count", "medium_count", "low_count",
         "total_penalty_exposure", "review_date"],
        as_dict=True,
        order_by="creation desc"
    )

    if not latest_register:
        return {"no_register": True}

    risks = frappe.db.get_all(
        "Compliance Risk Item",
        filters={"parent": latest_register.name},
        fields=["risk_title", "risk_category", "risk_level", "risk_score",
                "likelihood", "impact", "owner", "mitigation"],
        order_by="risk_score desc",
        limit=10
    )

    return {
        "register":      latest_register,
        "critical":      latest_register.critical_count or 0,
        "high":          latest_register.high_count or 0,
        "medium":        latest_register.medium_count or 0,
        "low":           latest_register.low_count or 0,
        "penalty_exposure": latest_register.total_penalty_exposure or 0,
        "top_risks":     risks,
    }


# ── Incidents Widget ──────────────────────────────────────────────────────────

def _get_incidents_summary(company):
    open_inc = frappe.db.get_all(
        "Compliance Incident",
        filters={"status": ["not in", ["Resolved", "Closed"]]},
        fields=["name", "incident_title", "incident_type", "obligation_type",
                "severity", "status", "incident_date", "penalty_amount"],
        order_by="incident_date desc",
        limit=10
    )
    total_penalty = frappe.db.sql("""
        SELECT COALESCE(SUM(penalty_amount), 0) FROM `tabCompliance Incident`
        WHERE status NOT IN ('Resolved', 'Closed')
    """)[0][0]

    by_type = frappe.db.sql("""
        SELECT incident_type, COUNT(*) as cnt FROM `tabCompliance Incident`
        WHERE status NOT IN ('Resolved', 'Closed')
        GROUP BY incident_type ORDER BY cnt DESC LIMIT 6
    """, as_dict=True)

    return {
        "open":          len(open_inc),
        "total_penalty": flt(total_penalty),
        "open_list":     open_inc,
        "by_type":       by_type,
    }


# ── Calendar Widget ───────────────────────────────────────────────────────────

def _get_calendar_upcoming(company, days_ahead=60):
    cutoff = add_days(nowdate(), days_ahead)
    lines  = frappe.db.sql("""
        SELECT cl.obligation_type, cl.fiscal_month, cl.due_date, cl.status,
               cl.assigned_to, cl.filing_reference, cr.requirement_name,
               cr.responsible_officer, cr.reminder_days_before
        FROM `tabCompliance Calendar Line` cl
        JOIN `tabCompliance Requirement` cr ON cr.name = cl.requirement
        JOIN `tabCompliance Calendar` cc ON cc.name = cl.parent
        WHERE cc.company  = %s
          AND cl.status   IN ('Pending', 'In Progress')
          AND cl.due_date BETWEEN %s AND %s
        ORDER BY cl.due_date ASC
        LIMIT 30
    """, (company, nowdate(), cutoff), as_dict=True)

    return {
        "upcoming": lines,
        "count":    len(lines),
    }


# ── Compliance Score ──────────────────────────────────────────────────────────

def _compute_score(company):
    """
    Overall compliance health score (0-100).
    Weighted average across: CLL paid %, license validity, no open incidents.
    """
    # CLL: 50% weight
    total_cll = frappe.db.count("Compliance Liability Ledger", {"company": company})
    paid_cll  = frappe.db.count("Compliance Liability Ledger", {"company": company, "status": "Paid"})
    cll_score = (paid_cll / total_cll * 100) if total_cll else 100.0

    # Licenses: 30% weight
    total_lic = frappe.db.count("License and Permit", {"company": company})
    valid_lic = frappe.db.count("License and Permit", {"company": company, "status": "Valid"})
    lic_score = (valid_lic / total_lic * 100) if total_lic else 100.0

    # Incidents: 20% weight (deduct 10 per open critical, 5 per open major)
    critical_inc = frappe.db.count("Compliance Incident", {
        "severity": "Critical", "status": ["not in", ["Resolved", "Closed"]]
    })
    major_inc = frappe.db.count("Compliance Incident", {
        "severity": "Major", "status": ["not in", ["Resolved", "Closed"]]
    })
    inc_score = max(0, 100 - (critical_inc * 10) - (major_inc * 5))

    overall = round(cll_score * 0.5 + lic_score * 0.3 + inc_score * 0.2, 1)

    return {
        "overall":   overall,
        "cll_score": round(cll_score, 1),
        "lic_score": round(lic_score, 1),
        "inc_score": round(inc_score, 1),
    }


# ── CLL Trend (12-month) ──────────────────────────────────────────────────────

def _get_cll_trend(company, obligation_type, months=12):
    result = frappe.db.sql("""
        SELECT fiscal_month,
               SUM(amount_calculated) AS liability,
               SUM(amount_paid)       AS paid,
               SUM(balance)           AS balance
        FROM `tabCompliance Liability Ledger`
        WHERE company         = %s
          AND obligation_type = %s
        GROUP BY fiscal_month
        ORDER BY fiscal_month DESC
        LIMIT %s
    """, (company, obligation_type, months), as_dict=True)
    return list(reversed(result))


# ── Per-obligation CLL list ───────────────────────────────────────────────────

@frappe.whitelist()
def get_cll_list(company, obligation_type, limit=24):
    """Return paginated CLL entries for the given obligation type — for tab grids."""
    data = frappe.db.get_all(
        "Compliance Liability Ledger",
        filters={"company": company, "obligation_type": obligation_type},
        fields=["name", "fiscal_month", "due_date", "amount_calculated",
                "amount_paid", "balance", "status", "penalty_incurred"],
        order_by="fiscal_month desc",
        limit=int(limit)
    )
    return data


# ── Manual run button ─────────────────────────────────────────────────────────

@frappe.whitelist()
def run_liability_generation_now(company, fiscal_month):
    """Called from JS 'Regenerate' button on dashboard."""
    from ecclesia.api.compliance.liability_engine import run_all_liability_generation
    return run_all_liability_generation(fiscal_month)


@frappe.whitelist()
def run_reconciliation_now(company, obligation_type=None):
    """Called from JS 'Reconcile' button."""
    from ecclesia.api.compliance.allocation_engine import reconcile_cll
    return reconcile_cll(company, obligation_type)


# ── AI Compliance Analysis ────────────────────────────────────────────────────

@frappe.whitelist()
def get_ai_compliance_analysis(company, fiscal_month=None):
    """
    Builds a comprehensive prompt from CLL data and calls the existing
    Anthropic API endpoint used across Ecclesia pages.
    """
    if not fiscal_month:
        d = getdate(nowdate())
        fiscal_month = f"{d.year:04d}-{d.month:02d}"

    summary = get_dashboard_summary(company, fiscal_month)

    # Build context
    overdue_count    = frappe.db.count("Compliance Liability Ledger",
                                        {"company": company, "status": "Overdue"})
    total_balance    = frappe.db.sql("""
        SELECT COALESCE(SUM(balance), 0) FROM `tabCompliance Liability Ledger`
        WHERE company = %s AND status NOT IN ('Paid', 'Exempt')
    """, (company,))[0][0]
    total_penalties  = frappe.db.sql("""
        SELECT COALESCE(SUM(penalty_incurred), 0) FROM `tabCompliance Liability Ledger`
        WHERE company = %s AND status = 'Overdue'
    """, (company,))[0][0]
    expired_licenses = frappe.db.count("License and Permit", {"company": company, "status": "Expired"})
    open_incidents   = frappe.db.count("Compliance Incident",
                                        {"status": ["not in", ["Resolved", "Closed"]]})

    tax = summary.get("tax", {})

    prompt = f"""You are an expert Nigerian compliance and regulatory affairs analyst.
Analyse this compliance data for {company} for period {fiscal_month} and provide:
1. An overall compliance risk assessment (Critical / High / Medium / Low)
2. Top 5 specific actions required in the next 7 days
3. Estimated regulatory penalty exposure
4. One strategic recommendation

Data summary:
- Compliance Score: {summary.get('compliance_score', {}).get('overall', 'N/A')}%
- VAT: Liability ₦{flt(tax.get('VAT',{}).get('liability',0)):,.0f} | Paid ₦{flt(tax.get('VAT',{}).get('paid',0)):,.0f} | Status: {tax.get('VAT',{}).get('status','N/A')}
- WHT: Liability ₦{flt(tax.get('WHT',{}).get('liability',0)):,.0f} | Status: {tax.get('WHT',{}).get('status','N/A')}
- PAYE: Liability ₦{flt(tax.get('PAYE',{}).get('liability',0)):,.0f} | Status: {tax.get('PAYE',{}).get('status','N/A')}
- Pension: Status: {summary.get('statutory',{}).get('Pension',{}).get('status','N/A')}
- Overdue CLL entries: {overdue_count}
- Total outstanding balance: ₦{flt(total_balance):,.0f}
- Accrued penalties: ₦{flt(total_penalties):,.0f}
- Expired licenses: {expired_licenses}
- Open incidents: {open_incidents}
- Upcoming obligations: {summary.get('calendar',{}).get('count', 0)} in next 60 days

Provide your analysis as structured JSON:
{{"risk_level":"Critical|High|Medium|Low","summary":"...","actions":[{{"priority":1,"action":"...","deadline":"...","authority":"..."}}],"penalty_exposure":"₦...", "strategic_recommendation":"..."}}
JSON only, no markdown."""

    # Call the existing AI endpoint
    try:
        from ecclesia.api.ai_diagnosis import get_ai_insight
        result = get_ai_insight(prompt=prompt, context="compliance_dashboard", max_tokens=1500)
        return {"success": True, "analysis": result}
    except Exception as e:
        frappe.log_error(f"Compliance AI analysis failed: {e}")
        return {"success": False, "error": str(e)}