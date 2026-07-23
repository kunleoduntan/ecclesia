# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/page/compliance_hq/compliance_hq.py
"""
ComplianceHQ — Unified Backend
All whitelisted methods for the ComplianceHQ v3 GRC dashboard page.
Path: ecclesia.ecclesia.page.compliance_hq.compliance_hq

Covers:
  · Overview + Statutory Tax (v2 CLL)
  · 9 GRC domains (v3)
  · Excel export with openpyxl
  · AI analysis via Claude API
  · Liability generation + CLL reconciliation
"""

import frappe
from frappe import _
from frappe.utils import (
    flt, nowdate, getdate, date_diff, add_days, get_last_day
)
import json
import base64
from io import BytesIO
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER SUMMARY — single call on dashboard load
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_dashboard_summary(company, fiscal_month=None):
    """
    Returns full KPI data for all Overview + Statutory tabs.
    Also embeds v3 domain summary so JS needs only one API call on load.
    """
    if not company:
        frappe.throw(_("Company is required"))

    if not fiscal_month:
        fiscal_month = nowdate()[:7]

    year, month = fiscal_month.split('-')
    period_start = f"{year}-{month}-01"
    period_end   = str(get_last_day(period_start))

    return {
        "fiscal_month":    fiscal_month,
        "tax":             _get_tax_status(company, period_start, period_end),
        "statutory":       _get_statutory_status(company, period_start, period_end),
        "licenses":        _get_license_status(company),
        "incidents":       _get_incidents(company),
        "calendar":        _get_calendar_entries(company, period_start, period_end),
        "tasks":           _get_open_tasks(company),
        "total_liability": _get_total_liability(company, period_start, period_end),
        "v3":              _v3_domain_summary(company),
    }


@frappe.whitelist()
def get_v3_domain_summary(company):
    """Returns KPI summary for all 9 GRC domains."""
    if not company:
        frappe.throw(_("Company is required"))
    return _v3_domain_summary(company)


@frappe.whitelist()
def get_full_compliance_score(company):
    """Holistic GRC score across all 9 domains (weighted)."""
    if not company:
        frappe.throw(_("Company is required"))

    v3 = _v3_domain_summary(company)

    def pct(ok, total):
        return round(ok / total * 100, 1) if total else 100.0

    scores = {
        "corporate": pct(
            v3["corporate"]["total_registers"] - v3["corporate"]["non_compliant"],
            max(v3["corporate"]["total_registers"], 1)
        ),
        "contracts": pct(v3["contracts"]["compliant"], max(v3["contracts"]["total"], 1)),
        "ndpr": pct(
            v3["ndpr"]["processing_records"] - v3["ndpr"]["dpia_missing"],
            max(v3["ndpr"]["processing_records"], 1)
        ),
        "aml": 100.0 if v3["aml"]["total_kyc"] == 0 else pct(
            v3["aml"]["total_kyc"] - v3["aml"]["kyc_expiring_30d"],
            v3["aml"]["total_kyc"]
        ),
        "labour": (
            100.0 if v3["labour"]["latest_status"] == "Compliant" else
            75.0  if v3["labour"]["latest_status"] == "Minor Issues" else
            50.0  if v3["labour"]["latest_status"] == "Major Issues" else 25.0
        ),
        "environmental": pct(v3["environmental"]["active"], max(v3["environmental"]["total"], 1)),
        "industry":      pct(v3["industry"]["submitted"],   max(v3["industry"]["total"],      1)),
        "fraud": (
            100.0 if v3["fraud"]["total_wb_reports"] == 0 else pct(
                v3["fraud"]["total_wb_reports"] - v3["fraud"]["under_investigation"],
                v3["fraud"]["total_wb_reports"]
            )
        ),
        "training": v3["training"]["mandatory_pct"],
    }

    weights = {
        "corporate": 0.10, "contracts": 0.08, "ndpr": 0.12,
        "aml": 0.15,       "labour": 0.12,    "environmental": 0.10,
        "industry": 0.10,  "fraud": 0.08,     "training": 0.05,
    }
    overall = sum(scores[k] * weights[k] for k in scores)

    return {
        "overall_v3":    round(overall, 1),
        "domain_scores": scores,
        "weights":       weights,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TAX & STATUTORY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_tax_status(company, period_start, period_end):
    result = {}
    for ob in ["VAT", "WHT", "PAYE", "CIT"]:
        row = frappe.db.sql("""
            SELECT status, total_liability, total_paid, balance_due
            FROM `tabCompliance Liability Ledger`
            WHERE company = %s AND obligation_type = %s
              AND period_start >= %s AND period_end <= %s
            ORDER BY period_start DESC LIMIT 1
        """, (company, ob, period_start, period_end), as_dict=True)
        if row:
            result[ob] = {
                "status":    row[0].status,
                "liability": flt(row[0].total_liability),
                "paid":      flt(row[0].total_paid),
                "balance":   flt(row[0].balance_due),
            }
        else:
            result[ob] = {"status": "Not Generated", "liability": 0, "paid": 0, "balance": 0}
    return result


def _get_statutory_status(company, period_start, period_end):
    result = {}
    for ob in ["Pension", "NHF", "NSITF", "ITF"]:
        row = frappe.db.sql("""
            SELECT status, total_liability, total_paid, balance_due
            FROM `tabCompliance Liability Ledger`
            WHERE company = %s AND obligation_type = %s
              AND period_start >= %s AND period_end <= %s
            ORDER BY period_start DESC LIMIT 1
        """, (company, ob, period_start, period_end), as_dict=True)
        if row:
            result[ob] = {
                "status":    row[0].status,
                "liability": flt(row[0].total_liability),
                "paid":      flt(row[0].total_paid),
                "balance":   flt(row[0].balance_due),
            }
        else:
            result[ob] = {"status": "Not Generated", "liability": 0, "paid": 0, "balance": 0}
    return result


def _get_license_status(company):
    valid = expiring = expired = 0
    expiring_list = []

    if frappe.db.table_exists("tabLicense Management"):
        lics = frappe.db.get_all("License Management",
            filters={"company": company},
            fields=["name", "license_name", "license_type",
                    "current_expiry_date", "status", "days_to_expiry"]
        )
        for l in lics:
            if l.status == "Active":          valid += 1
            elif l.status == "Expiring Soon": expiring += 1; expiring_list.append(l)
            elif l.status == "Expired":       expired += 1
    return {
        "valid": valid, "expiring": expiring, "expired": expired,
        "expiring_list": sorted(expiring_list, key=lambda x: x.days_to_expiry or 999)[:30],
    }


def _get_incidents(company):
    if not frappe.db.table_exists("tabCompliance Incident"):
        return {"recent": [], "by_type": [], "open": 0}

    recent = frappe.db.get_all("Compliance Incident",
        filters={"company": company},
        fields=["name", "incident_title", "incident_type", "status", "incident_date"],
        order_by="incident_date desc", limit=20
    )
    by_type = frappe.db.sql("""
        SELECT incident_type, COUNT(*) AS cnt
        FROM `tabCompliance Incident`
        WHERE company=%s GROUP BY incident_type
    """, (company,), as_dict=True)
    open_count = frappe.db.count("Compliance Incident",
        {"company": company, "status": ["!=", "Closed"]})
    return {"recent": recent, "by_type": by_type, "open": open_count}


def _get_calendar_entries(company, period_start, period_end):
    try:
        rows = frappe.db.sql("""
            SELECT ccl.obligation_type, ccl.period_label, ccl.due_date,
                   ccl.status, ccl.assigned_to, ccl.compliance_domain,
                   cr.requirement_name
            FROM `tabCompliance Calendar Line` ccl
            JOIN `tabCompliance Calendar` cc ON cc.name = ccl.parent
            LEFT JOIN `tabCompliance Requirement` cr ON cr.name = ccl.requirement
            WHERE cc.company = %s AND ccl.due_date >= %s
            ORDER BY ccl.due_date ASC LIMIT 30
        """, (company, period_start), as_dict=True)
        return {"upcoming": rows, "entries": rows, "count": len(rows)}
    except Exception:
        upcoming = frappe.db.get_all("Compliance Liability Ledger",
            filters={"company": company,
                     "status": ["in", ["Open", "Partially Paid"]],
                     "due_date": [">=", period_start]},
            fields=["name", "obligation_type", "fiscal_month", "due_date", "status", "balance_due"],
            order_by="due_date asc", limit=20
        )
        rows = [{"obligation_type": r.obligation_type, "period_label": r.fiscal_month,
                 "due_date": r.due_date, "status": r.status,
                 "requirement_name": r.obligation_type} for r in upcoming]
        return {"upcoming": rows, "entries": rows, "count": len(rows)}


def _get_open_tasks(company):
    if not frappe.db.table_exists("tabCompliance Task"):
        return {"open": []}
    tasks = frappe.db.get_all("Compliance Task",
        filters={"company": company, "status": ["!=", "Completed"]},
        fields=["name", "task_title", "priority", "target_completion", "status"],
        order_by="priority asc, target_completion asc", limit=20
    )
    return {"open": tasks}


def _get_total_liability(company, period_start, period_end):
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(balance_due), 0) AS total
        FROM `tabCompliance Liability Ledger`
        WHERE company = %s AND period_start >= %s
          AND period_end <= %s AND status != 'Fully Paid'
    """, (company, period_start, period_end), as_dict=True)
    return flt(result[0].total) if result else 0


# ══════════════════════════════════════════════════════════════════════════════
#  V3 DOMAIN SUMMARY (9 GRC domains)
# ══════════════════════════════════════════════════════════════════════════════

def _v3_domain_summary(company):
    return {
        "corporate":     _corp(company),
        "contracts":     _contracts(company),
        "ndpr":          _ndpr(company),
        "aml":           _aml(company),
        "labour":        _labour(company),
        "environmental": _env(company),
        "industry":      _industry(company),
        "fraud":         _fraud(company),
        "training":      _training(company),
    }


def _corp(company):
    total        = frappe.db.count("Corporate Compliance Register", {"company": company})
    non_compliant= frappe.db.count("Corporate Compliance Register",
                        {"company": company, "overall_status": "Non-Compliant"})
    ar_overdue   = frappe.db.count("Corporate Compliance Register",
                        {"company": company, "annual_return_status": "Overdue"})
    agm_missed   = frappe.db.count("Corporate Compliance Register",
                        {"company": company, "agm_held_on_time": 0})
    cac_out      = frappe.db.count("Board Resolution",
                        {"company": company, "cac_filing_required": 1, "cac_filed": 0})
    res_pending  = frappe.db.count("Board Resolution",
                        {"company": company, "implementation_status": ["!=", "Implemented"]})
    return {
        "total_registers": total, "non_compliant": non_compliant,
        "annual_return_overdue": ar_overdue, "agm_missed": agm_missed,
        "cac_filings_outstanding": cac_out, "resolutions_pending": res_pending,
    }


def _contracts(company):
    total         = frappe.db.count("Contract Compliance Record", {"company": company})
    compliant     = frappe.db.count("Contract Compliance Record",
                        {"company": company, "compliance_status": "Compliant"})
    material      = frappe.db.count("Contract Compliance Record",
                        {"company": company, "compliance_status": "Material Breach"})
    minor         = frappe.db.count("Contract Compliance Record",
                        {"company": company, "compliance_status": "Minor Breach"})
    term_risk     = frappe.db.count("Contract Compliance Record",
                        {"company": company, "compliance_status": "Termination Risk"})
    avg_sla = frappe.db.sql("""
        SELECT AVG(sla_compliance_pct) FROM `tabContract Compliance Record`
        WHERE company=%s
    """, (company,))[0][0] or 0
    return {
        "total": total, "compliant": compliant, "material_breach": material,
        "minor_breach": minor, "termination_risk": term_risk,
        "avg_sla": round(flt(avg_sla), 1),
    }


def _ndpr(company):
    recs       = frappe.db.count("Data Processing Record", {"company": company})
    sensitive  = frappe.db.count("Data Processing Record",
                     {"company": company, "is_sensitive_data": 1})
    dpia_miss  = frappe.db.count("Data Processing Record",
                     {"company": company, "is_sensitive_data": 1, "privacy_impact_done": 0})
    nitda      = frappe.db.count("Data Processing Record",
                     {"company": company, "nitda_registered": 1})
    open_br    = frappe.db.count("Data Breach Register",
                     {"company": company, "status": ["!=", "Closed"]})
    late_notif = frappe.db.count("Data Breach Register",
                     {"company": company, "late_notification_flag": 1})
    return {
        "processing_records": recs, "sensitive_data_records": sensitive,
        "dpia_missing": dpia_miss, "nitda_registered": nitda,
        "open_breaches": open_br, "late_notifications": late_notif,
    }


def _aml(company):
    total      = frappe.db.count("AML KYC Record", {"company": company})
    high_risk  = frappe.db.count("AML KYC Record",
                     {"company": company, "risk_rating": ["in", ["High","PEP — High","Sanctioned — Blocked"]]})
    pep        = frappe.db.count("AML KYC Record", {"company": company, "is_pep": 1})
    sanction   = frappe.db.count("AML KYC Record", {"company": company, "sanctions_match": 1})
    exp30      = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabAML KYC Record`
        WHERE company=%s AND kyc_expiry_date IS NOT NULL
          AND DATEDIFF(kyc_expiry_date, CURDATE()) BETWEEN 0 AND 30
    """, (company,))[0][0]
    strs_pend  = frappe.db.count("Suspicious Transaction Report",
                     {"company": company, "nfiu_submitted": 0,
                      "status": ["!=", "Closed — No Action"]})
    return {
        "total_kyc": total, "high_risk": high_risk, "pep_count": pep,
        "sanctions_match": sanction, "kyc_expiring_30d": int(exp30),
        "strs_pending_nfiu": strs_pend,
    }


def _labour(company):
    total_p  = frappe.db.count("Expatriate Permit Register", {"company": company})
    expired  = frappe.db.count("Expatriate Permit Register",
                   {"company": company, "status": "Expired"})
    expiring = frappe.db.count("Expatriate Permit Register",
                   {"company": company, "status": "Expiring Soon"})
    latest   = frappe.db.get_all("Labour Compliance Tracker",
        filters={"company": company},
        fields=["period_label","overall_status","minimum_wage_compliant","pencom_all_registered"],
        order_by="review_date desc", limit=1
    )
    l = latest[0] if latest else {}
    return {
        "total_permits": total_p, "expired_permits": expired, "expiring_permits": expiring,
        "latest_status": l.get("overall_status", "No Data"),
        "latest_period": l.get("period_label", "—"),
        "wage_compliant":   l.get("minimum_wage_compliant", None),
        "pencom_compliant": l.get("pencom_all_registered", None),
    }


def _env(company):
    total   = frappe.db.count("Environmental Compliance Record", {"company": company})
    active  = frappe.db.count("Environmental Compliance Record",
                  {"company": company, "status": "Active"})
    exp     = frappe.db.count("Environmental Compliance Record",
                  {"company": company, "status": "Expired"})
    soon    = frappe.db.count("Environmental Compliance Record",
                  {"company": company, "status": "Expiring Soon"})
    pend    = frappe.db.sql("""
        SELECT COALESCE(SUM(corrective_actions_pending),0)
        FROM `tabEnvironmental Compliance Record` WHERE company=%s
    """, (company,))[0][0]
    major   = frappe.db.count("Environmental Compliance Record",
                  {"company": company, "last_inspection_result": "Major Non-Compliance"})
    return {
        "total": total, "active": active, "expired": exp,
        "expiring_soon": soon, "pending_actions": int(pend), "major_non_compliance": major,
    }


def _industry(company):
    total   = frappe.db.count("Regulatory Return", {"company": company})
    overdue = frappe.db.count("Regulatory Return", {"company": company, "status": "Overdue"})
    late    = frappe.db.count("Regulatory Return", {"company": company, "late_flag": 1})
    pending = frappe.db.count("Regulatory Return",
                  {"company": company, "status": ["in", ["Pending","Preparing"]]})
    submitted = frappe.db.count("Regulatory Return",
                  {"company": company, "status": ["in", ["Submitted","Late Submitted","Accepted"]]})
    penalty = frappe.db.sql("""
        SELECT COALESCE(SUM(penalty_for_non_filing),0)
        FROM `tabRegulatory Return` WHERE company=%s
    """, (company,))[0][0]
    return {
        "total": total, "overdue": overdue, "late": late,
        "pending": pending, "submitted": submitted, "total_penalty": flt(penalty),
    }


def _fraud(company):
    total_wb = frappe.db.count("Whistleblower Report", {"company": company})
    invest   = frappe.db.count("Whistleblower Report",
                   {"company": company, "status": "Under Investigation"})
    escalated= frappe.db.count("Whistleblower Report",
                   {"company": company, "status": "Escalated"})
    subst    = frappe.db.count("Whistleblower Report",
                   {"company": company, "status": "Closed — Substantiated"})
    total_coi= frappe.db.count("Conflict of Interest Declaration", {"company": company})
    coi_pend = frappe.db.count("Conflict of Interest Declaration",
                   {"company": company, "approval_status": "Pending"})
    return {
        "total_wb_reports": total_wb, "under_investigation": invest,
        "escalated": escalated, "substantiated": subst,
        "total_coi": total_coi, "coi_pending_review": coi_pend,
    }


def _training(company):
    total    = frappe.db.count("Compliance Training Record", {"company": company})
    if not total:
        return {"mandatory_pct": 0, "total_records": 0, "mandatory_completed": 0,
                "mandatory_total": 0, "failed": 0, "unique_employees": 0,
                "upcoming_sessions": 0, "below_target": 0}
    failed   = frappe.db.count("Compliance Training Record",
                   {"company": company, "completion_status": "Failed"})
    m_total  = frappe.db.count("Compliance Training Record",
                   {"company": company, "is_mandatory": 1})
    m_done   = frappe.db.count("Compliance Training Record",
                   {"company": company, "is_mandatory": 1,
                    "completion_status": ["in", ["Completed","Passed"]]})
    unique   = frappe.db.sql("""
        SELECT COUNT(DISTINCT employee) FROM `tabCompliance Training Record`
        WHERE company=%s
    """, (company,))[0][0]
    upcoming = frappe.db.count("Compliance Training Calendar",
                   {"company": company, "status": ["in", ["Planned","Scheduled"]]})
    return {
        "total_records": total, "failed": failed,
        "mandatory_total": m_total, "mandatory_completed": m_done,
        "mandatory_pct": round(m_done / m_total * 100, 1) if m_total else 0,
        "unique_employees": int(unique), "upcoming_sessions": upcoming,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TAB DETAIL ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_corporate_governance_tab(company):
    registers = frappe.db.get_all("Corporate Compliance Register",
        filters={"company": company},
        fields=["name","company","fiscal_year","rc_number",
                "annual_return_status","agm_held_on_time","overall_status"]
    )
    pending_resolutions = frappe.db.get_all("Board Resolution",
        filters={"company": company,
                 "implementation_status": ["!=", "Implemented"]},
        fields=["name","resolution_number","meeting_type","meeting_date",
                "resolution_category","cac_filing_required","cac_filed","implementation_status"]
    )
    register_entries = frappe.db.sql("""
        SELECT sre.register_type, COUNT(*) as count
        FROM `tabStatutory Register Entry` sre
        WHERE sre.corporate_register IN (
            SELECT name FROM `tabCorporate Compliance Register` WHERE company=%s
        )
        GROUP BY sre.register_type
    """, (company,), as_dict=True)
    return {
        **_corp(company),
        "registers": registers,
        "pending_resolutions": pending_resolutions,
        "register_entries": register_entries,
    }


@frappe.whitelist()
def get_contracts_tab(company):
    records = frappe.db.get_all("Contract Compliance Record",
        filters={"company": company},
        fields=["name","compliance_title","vendor","sla_compliance_pct",
                "open_breaches","contract_end","compliance_status","contract_value"],
        order_by="modified desc", limit=50
    )
    expiring_60 = frappe.db.get_all("Contract Compliance Record",
        filters={"company": company,
                 "contract_end": ["between", [nowdate(), add_days(nowdate(), 60)]],
                 "compliance_status": ["!=", "Expired"]},
        fields=["name","compliance_title","vendor","contract_end",
                "compliance_status","contract_value","sla_compliance_pct"],
        order_by="contract_end asc"
    )
    return {**_contracts(company), "records": records, "expiring_60_days": expiring_60}


@frappe.whitelist()
def get_ndpr_tab(company):
    open_breaches_detail = frappe.db.get_all("Data Breach Register",
        filters={"company": company, "status": ["!=", "Closed"]},
        fields=["name","breach_title","breach_type","severity",
                "data_subjects_affected","nitda_notified","status","breach_date",
                "late_notification_flag"]
    )
    reviews_due = frappe.db.get_all("Data Processing Record",
        filters={"company": company, "status": "Active",
                 "next_review_date": ["<=", add_days(nowdate(), 30)]},
        fields=["name","processing_title","legal_basis","is_sensitive_data",
                "privacy_impact_done","next_review_date","dpo"],
        order_by="next_review_date asc"
    )
    return {**_ndpr(company),
            "open_breaches_detail": open_breaches_detail,
            "reviews_due_30_days": reviews_due}


@frappe.whitelist()
def get_aml_tab(company):
    high_risk_parties = frappe.db.get_all("AML KYC Record",
        filters={"company": company,
                 "risk_rating": ["in", ["High","PEP — High","Sanctioned — Blocked"]]},
        fields=["name","party_name_display","party_type","risk_rating",
                "kyc_level","kyc_expiry_date","is_pep","sanctions_match"]
    )
    pending_strs = frappe.db.get_all("Suspicious Transaction Report",
        filters={"company": company, "nfiu_submitted": 0,
                 "status": ["not in", ["Closed — No Action"]]},
        fields=["name","str_title","report_type","transaction_date",
                "transaction_amount","party_name","status"],
        order_by="transaction_date desc", limit=10
    )
    return {**_aml(company),
            "high_risk_parties": high_risk_parties,
            "pending_nfiu_strs": pending_strs}


@frappe.whitelist()
def get_labour_tab(company):
    expiring_permits = frappe.db.get_all("Expatriate Permit Register",
        filters={"company": company,
                 "status": ["in", ["Active","Expiring Soon"]],
                 "expiry_date": ["<=", add_days(nowdate(), 90)]},
        fields=["name","permit_title","employee","permit_type",
                "expiry_date","days_to_expiry","status","renewal_cost"],
        order_by="days_to_expiry asc"
    )
    labour_trend = frappe.db.get_all("Labour Compliance Tracker",
        filters={"company": company, "docstatus": 1},
        fields=["period_label","overall_status","minimum_wage_compliant",
                "working_hours_compliant","pencom_all_registered",
                "nhf_all_registered","employment_contracts_compliant","total_employees"],
        order_by="period_label desc", limit=12
    )
    return {**_labour(company),
            "expiring_permits": expiring_permits[:20],
            "labour_trend": labour_trend}


@frappe.whitelist()
def get_environmental_tab(company):
    expiring_90_days = frappe.db.get_all("Environmental Compliance Record",
        filters={"company": company,
                 "status": ["in", ["Active","Expiring Soon"]],
                 "expiry_date": ["<=", add_days(nowdate(), 90)]},
        fields=["name","permit_title","permit_type","issuing_authority","facility",
                "expiry_date","days_to_expiry","status","renewal_cost","responsible_officer"],
        order_by="expiry_date asc"
    )
    by_type = frappe.db.sql("""
        SELECT permit_type, COUNT(*) as count,
               SUM(CASE WHEN status='Expired' THEN 1 ELSE 0 END) as expired
        FROM `tabEnvironmental Compliance Record`
        WHERE company=%s GROUP BY permit_type ORDER BY count DESC
    """, (company,), as_dict=True)
    return {**_env(company),
            "expiring_90_days": expiring_90_days[:20],
            "by_permit_type": by_type}


@frappe.whitelist()
def get_industry_tab(company):
    overdue_returns = frappe.db.get_all("Regulatory Return",
        filters={"company": company,
                 "status": ["in", ["Overdue","Pending","Late Submitted","Preparing"]]},
        fields=["name","return_title","authority","return_type","period_covered",
                "due_date","late_flag","penalty_for_non_filing","status","filed_by"],
        order_by="due_date asc", limit=20
    )
    by_authority = frappe.db.sql("""
        SELECT authority, COUNT(*) as total,
               SUM(CASE WHEN status='Overdue' THEN 1 ELSE 0 END) as overdue,
               SUM(CASE WHEN late_flag=1 THEN 1 ELSE 0 END) as late
        FROM `tabRegulatory Return`
        WHERE company=%s GROUP BY authority ORDER BY total DESC
    """, (company,), as_dict=True)
    return {**_industry(company),
            "overdue_returns": overdue_returns,
            "by_authority": by_authority}


@frappe.whitelist()
def get_fraud_tab(company):
    open_reports = frappe.db.get_all("Whistleblower Report",
        filters={"company": company,
                 "status": ["in", ["Received","Under Investigation","Escalated"]]},
        fields=["name","report_code","received_date","channel","report_category",
                "severity","status","assigned_investigator","estimated_financial_impact"],
        order_by="received_date desc", limit=15
    )
    pending_coi = frappe.db.get_all("Conflict of Interest Declaration",
        filters={"company": company, "approval_status": "Pending", "docstatus": 1},
        fields=["name","employee","declaration_type","declaration_date",
                "has_conflict","conflict_type","financial_value"],
        order_by="declaration_date desc"
    )
    by_category = frappe.db.sql("""
        SELECT report_category, COUNT(*) as count,
               SUM(CASE WHEN status IN ('Under Investigation','Escalated') THEN 1 ELSE 0 END) as open
        FROM `tabWhistleblower Report`
        WHERE company=%s GROUP BY report_category ORDER BY count DESC LIMIT 8
    """, (company,), as_dict=True)
    return {**_fraud(company),
            "open_reports": open_reports,
            "pending_coi_reviews": pending_coi,
            "by_category": by_category}


@frappe.whitelist()
def get_training_tab(company, fiscal_year=None):
    by_category = frappe.db.sql("""
        SELECT training_category, COUNT(*) as total,
               SUM(CASE WHEN completion_status IN ('Completed','Passed') AND is_mandatory=1
                        THEN 1 ELSE 0 END) as completed,
               SUM(CASE WHEN is_mandatory=1 THEN 1 ELSE 0 END) as mandatory,
               SUM(CASE WHEN completion_status='Failed' THEN 1 ELSE 0 END) as failed
        FROM `tabCompliance Training Record`
        WHERE company=%s AND docstatus=1
        GROUP BY training_category ORDER BY mandatory DESC
    """, (company,), as_dict=True)
    upcoming = frappe.db.get_all("Compliance Training Calendar",
        filters={"company": company, "docstatus": 1,
                 "status": ["in", ["Planned","Scheduled"]],
                 "scheduled_date": [">=", nowdate()]},
        fields=["name","calendar_title","training_category","scheduled_date",
                "target_headcount","actual_attendees","actual_completion_pct",
                "completion_target_pct","is_mandatory","venue"],
        order_by="scheduled_date asc", limit=10
    )
    overdue_employees = frappe.db.sql("""
        SELECT e.employee_name, e.department, r.training_category,
               r.certificate_expiry, r.completion_status
        FROM `tabCompliance Training Record` r
        JOIN `tabEmployee` e ON e.name = r.employee
        WHERE r.company=%s AND r.is_mandatory=1 AND r.docstatus=1
          AND (r.completion_status='Failed'
               OR (r.certificate_expiry IS NOT NULL AND r.certificate_expiry < CURDATE()))
        LIMIT 20
    """, (company,), as_dict=True)
    return {**_training(company),
            "by_category": by_category,
            "upcoming_sessions": upcoming,
            "overdue_employees": overdue_employees}


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITY ACTIONS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_liability_generation_now(company, fiscal_month=None):
    """Trigger liability generation for the given month."""
    if not company:
        return {"success": False, "error": "Company required"}
    if not fiscal_month:
        fiscal_month = nowdate()[:7]
    try:
        from ecclesia.api.compliance.liability_engine_v2 import (
            run_vat_generation, run_wht_generation, run_payroll_liabilities
        )
        results = {
            "VAT":     run_vat_generation(company, fiscal_month),
            "WHT":     run_wht_generation(company, fiscal_month),
            "payroll": run_payroll_liabilities(company, fiscal_month),
        }
        frappe.db.commit()
        return {"success": True, "results": results,
                "message": f"Liabilities generated for {company} / {fiscal_month}"}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Liability generation failed: {e}", "ComplianceHQ")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def run_reconciliation_now(company=None):
    """Reconcile all CLL entries — recompute balance_due and status."""
    try:
        frappe.db.sql("""
            UPDATE `tabCompliance Liability Ledger`
            SET balance_due = total_liability - total_paid,
                status = CASE
                    WHEN total_liability = total_paid AND total_liability > 0 THEN 'Fully Paid'
                    WHEN total_paid > 0 AND total_paid < total_liability THEN 'Partially Paid'
                    WHEN due_date < CURDATE() AND total_liability > total_paid THEN 'Overdue'
                    ELSE status END,
                last_reconciled_on = NOW()
            WHERE company = %s OR %s IS NULL
        """, (company, company))
        updated = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
        frappe.db.commit()
        return {"success": True, "reconciled": int(updated),
                "message": f"Reconciled {updated} CLL entries"}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"CLL reconciliation failed: {e}", "ComplianceHQ")
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#  AI COMPLIANCE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_ai_compliance_analysis(company, fiscal_month=None):
    """
    Builds a prompt from live CLL + v3 domain data and calls Claude API.
    Returns: risk_level, summary, actions, penalty_exposure,
             strategic_recommendation.
    """
    if not company:
        return {"success": False, "error": "Company required"}
    if not fiscal_month:
        fiscal_month = nowdate()[:7]

    summary = get_dashboard_summary(company, fiscal_month)
    scores  = get_full_compliance_score(company)
    v3      = summary.get("v3", {})
    tax     = summary.get("tax", {})
    overall = scores.get("overall_v3", 0)

    overdue_cll = frappe.db.count("Compliance Liability Ledger",
        {"company": company, "status": "Overdue"})
    total_balance = frappe.db.sql("""
        SELECT COALESCE(SUM(balance_due),0)
        FROM `tabCompliance Liability Ledger`
        WHERE company=%s AND status NOT IN ('Fully Paid','Exempt')
    """, (company,))[0][0]
    total_penalties = frappe.db.sql("""
        SELECT COALESCE(SUM(penalty_incurred),0)
        FROM `tabCompliance Liability Ledger`
        WHERE company=%s AND status='Overdue'
    """, (company,))[0][0]

    def fmt(v): return f"₦{flt(v):,.0f}"

    prompt = f"""You are a senior Nigerian regulatory compliance expert.
Analyse this compliance data for {company} for period {fiscal_month} and respond ONLY with valid JSON.

STATUTORY DATA:
- Overall GRC Score: {overall}%
- VAT: {tax.get('VAT',{}).get('status','N/A')} | Balance: {fmt(tax.get('VAT',{}).get('balance',0))}
- WHT: {tax.get('WHT',{}).get('status','N/A')} | Balance: {fmt(tax.get('WHT',{}).get('balance',0))}
- PAYE: {tax.get('PAYE',{}).get('status','N/A')}
- Overdue CLL entries: {overdue_cll}
- Total outstanding balance: {fmt(total_balance)}
- Accrued penalties: {fmt(total_penalties)}

GRC DOMAIN DATA:
- Corporate — non-compliant registers: {v3.get('corporate',{}).get('non_compliant',0)}
- Contracts — material breaches: {v3.get('contracts',{}).get('material_breach',0)}
- NDPR — open data breaches: {v3.get('ndpr',{}).get('open_breaches',0)}, late NITDA notifications: {v3.get('ndpr',{}).get('late_notifications',0)}
- AML — high-risk parties: {v3.get('aml',{}).get('high_risk',0)}, sanctions matches: {v3.get('aml',{}).get('sanctions_match',0)}
- Labour — expired permits: {v3.get('labour',{}).get('expired_permits',0)}
- Environmental — expired permits: {v3.get('environmental',{}).get('expired',0)}
- Regulatory — returns overdue: {v3.get('industry',{}).get('overdue',0)}, total penalty exposure: {fmt(v3.get('industry',{}).get('total_penalty',0))}
- Integrity — reports under investigation: {v3.get('fraud',{}).get('under_investigation',0)}
- Training — mandatory completion: {v3.get('training',{}).get('mandatory_pct',0):.0f}%

Respond ONLY with this JSON (no markdown, no backticks):
{{"risk_level":"Critical|High|Medium|Low","summary":"2-3 sentence executive summary","penalty_exposure":"estimated total e.g. ₦2.5M","actions":[{{"action":"specific action","deadline":"timeframe","authority":"regulatory body"}}],"strategic_recommendation":"one sentence"}}"""

    try:
        import requests, re

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        data = response.json()
        text = "".join(b.get("text","") for b in data.get("content",[])
                       if b.get("type") == "text")

        match = re.search(r'\{[\s\S]*\}', text)
        analysis = json.loads(match.group()) if match else {"summary": text[:500]}
        return {"success": True, "analysis": {"response": analysis},
                "fiscal_month": fiscal_month}
    except Exception as e:
        frappe.log_error(f"AI compliance analysis failed: {e}", "ComplianceHQ")
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#  EXCEL EXPORT
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def export_compliance_report(company, fiscal_month=None, format="xlsx"):
    """Generate and return a base64-encoded Excel compliance report."""
    if not company:
        frappe.throw(_("Company is required"))
    if not fiscal_month:
        fiscal_month = nowdate()[:7]

    summary = get_dashboard_summary(company, fiscal_month)
    scores  = get_full_compliance_score(company)

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        frappe.throw(_("openpyxl is required. Run: pip install openpyxl --break-system-packages"))

    C = {
        "navy":   "1E3A5F",
        "white":  "FFFFFF",
        "grn":    "059669",
        "grn_lt": "D1FAE5",
        "red":    "DC2626",
        "red_lt": "FEE2E2",
        "amb":    "D97706",
        "amb_lt": "FEF3C7",
        "sky":    "0EA5E9",
        "sky_lt": "E0F2FE",
        "bg":     "F8FAFC",
        "brd":    "E2E8F0",
    }

    def hdr_fill(color=None): return PatternFill("solid", fgColor=color or C["navy"])
    def cell_fill(color):     return PatternFill("solid", fgColor=color)
    def bold(size=11, color="000000", italic=False):
        return Font(bold=True, size=size, color=color, italic=italic)
    def thin_border():
        s = Side(style="thin", color=C["brd"])
        return Border(left=s, right=s, top=s, bottom=s)
    def center(): return Alignment(horizontal="center", vertical="center")

    def style_header_row(ws, row, cols, bg=None):
        for col in range(1, cols + 1):
            c = ws.cell(row=row, column=col)
            c.font  = bold(10, C["white"])
            c.fill  = hdr_fill(bg)
            c.alignment = center()
            c.border = thin_border()

    wb = openpyxl.Workbook()

    # ── Sheet 1: Executive Dashboard ─────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Executive Dashboard"
    ws1.freeze_panes = "A3"
    ws1.column_dimensions["A"].width = 28
    ws1.column_dimensions["B"].width = 16
    ws1.column_dimensions["C"].width = 18
    ws1.column_dimensions["D"].width = 14

    ws1.merge_cells("A1:D1")
    ws1["A1"] = f"🏛️  ComplianceHQ — Executive Report  |  {company}  |  {fiscal_month}"
    ws1["A1"].font = bold(14, C["navy"])
    ws1["A1"].fill = cell_fill(C["sky_lt"])
    ws1["A1"].alignment = center()

    overall = scores.get("overall_v3", 0)
    ov_color = C["grn"] if overall >= 80 else C["amb"] if overall >= 60 else C["red"]

    ws1["A2"] = f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}"
    ws1["A2"].font = Font(size=9, color="64748B", italic=True)
    ws1["C2"] = f"Overall GRC Score: {overall:.1f}%"
    ws1["C2"].font = bold(11, ov_color)

    row = 4
    ws1.merge_cells(f"A{row}:D{row}")
    ws1[f"A{row}"] = "📊 DOMAIN SCORES"
    ws1[f"A{row}"].font = bold(11, C["navy"])
    row += 1

    headers = ["Domain", "Score", "Status", "Key Issues"]
    for col, h in enumerate(headers, 1):
        ws1.cell(row=row, column=col, value=h)
    style_header_row(ws1, row, 4)
    row += 1

    domain_meta = [
        ("corporate",    "🏢 Governance"),
        ("contracts",    "📄 Contracts"),
        ("ndpr",         "🔒 NDPR"),
        ("aml",          "🕵️  AML & KYC"),
        ("labour",       "👷 Labour"),
        ("environmental","🌿 Environmental"),
        ("industry",     "🏭 Regulatory"),
        ("fraud",        "🚨 Integrity"),
        ("training",     "🎓 Training"),
    ]
    v3 = summary.get("v3", {})
    issue_map = {
        "corporate":     v3.get("corporate",{}).get("non_compliant",0),
        "contracts":     v3.get("contracts",{}).get("material_breach",0),
        "ndpr":          v3.get("ndpr",{}).get("open_breaches",0),
        "aml":           v3.get("aml",{}).get("high_risk",0),
        "labour":        v3.get("labour",{}).get("expired_permits",0),
        "environmental": v3.get("environmental",{}).get("expired",0),
        "industry":      v3.get("industry",{}).get("overdue",0),
        "fraud":         v3.get("fraud",{}).get("under_investigation",0),
        "training":      0 if (v3.get("training",{}).get("mandatory_pct",100) or 100) >= 80 else 1,
    }
    ds = scores.get("domain_scores", {})
    for key, label in domain_meta:
        score  = round(flt(ds.get(key, 0)), 1)
        status = "Compliant" if score >= 80 else "Minor Issues" if score >= 60 else "Major Issues"
        sc_col = C["grn"] if score >= 80 else C["amb"] if score >= 60 else C["red"]
        bg_lt  = C["grn_lt"] if score >= 80 else C["amb_lt"] if score >= 60 else C["red_lt"]

        ws1.cell(row=row, column=1, value=label).font = bold(10)
        c_score = ws1.cell(row=row, column=2, value=f"{score}%")
        c_score.font = bold(10, sc_col)
        c_score.alignment = center()
        c_score.fill = cell_fill(bg_lt)
        ws1.cell(row=row, column=3, value=status).font = Font(size=10, color=sc_col)
        c_iss = ws1.cell(row=row, column=4, value=issue_map.get(key, 0))
        c_iss.alignment = center()
        for col in range(1, 5):
            ws1.cell(row=row, column=col).border = thin_border()
        row += 1

    # ── Sheet 2: Tax & Statutory ──────────────────────────────────────────────
    ws2 = wb.create_sheet("Tax & Statutory")
    for col, w in zip("ABCDEF", [22, 18, 18, 18, 18, 14]):
        ws2.column_dimensions[col].width = w

    ws2.merge_cells("A1:F1")
    ws2["A1"] = f"💰  Tax & Statutory Obligations — {company}  |  {fiscal_month}"
    ws2["A1"].font = bold(13, C["navy"])
    ws2["A1"].fill = cell_fill(C["sky_lt"])
    ws2["A1"].alignment = center()

    for section, label, obligations in [
        ("tax",       "TAX OBLIGATIONS",       ["VAT","WHT","PAYE","CIT"]),
        ("statutory", "STATUTORY OBLIGATIONS", ["Pension","NHF","NSITF","ITF"]),
    ]:
        row = ws2.max_row + 2
        ws2.merge_cells(f"A{row}:F{row}")
        ws2[f"A{row}"] = f"📋 {label}"
        ws2[f"A{row}"].font = bold(11, C["navy"])
        row += 1

        hds = ["Obligation","Status","Liability (₦)","Paid (₦)","Balance (₦)","Paid %"]
        for col, h in enumerate(hds, 1):
            ws2.cell(row=row, column=col, value=h)
        style_header_row(ws2, row, 6)
        row += 1

        data = summary.get(section, {})
        for ob in obligations:
            d       = data.get(ob, {})
            liab    = flt(d.get("liability", 0))
            paid    = flt(d.get("paid", 0))
            balance = flt(d.get("balance", 0))
            pct     = round(paid / liab * 100) if liab > 0 else 0
            status  = d.get("status","Not Generated")
            sc      = C["grn"] if status == "Fully Paid" else C["red"] if status in ("Overdue","Expired") else C["amb"]

            ws2.cell(row=row, column=1, value=ob).font = bold(10)
            c_st = ws2.cell(row=row, column=2, value=status)
            c_st.font  = Font(size=10, color=sc, bold=True)
            ws2.cell(row=row, column=3, value=liab).number_format    = "#,##0.00"
            ws2.cell(row=row, column=4, value=paid).number_format     = "#,##0.00"
            ws2.cell(row=row, column=5, value=balance).number_format  = "#,##0.00"
            c_pct = ws2.cell(row=row, column=6, value=f"{pct}%")
            c_pct.alignment = center()
            c_pct.font = Font(size=10, color=sc, bold=True)
            for col in range(1, 7):
                ws2.cell(row=row, column=col).border = thin_border()
            row += 1

    # ── Sheet 3: Licenses & Permits ───────────────────────────────────────────
    ws3 = wb.create_sheet("Licenses & Permits")
    for col, w in zip("ABCDEF", [30, 20, 16, 16, 16, 16]):
        ws3.column_dimensions[col].width = w

    ws3.merge_cells("A1:F1")
    ws3["A1"] = f"🎖️  Licenses & Permits — {company}"
    ws3["A1"].font = bold(13, C["navy"])
    ws3["A1"].fill = cell_fill(C["sky_lt"])
    ws3["A1"].alignment = center()

    lic = summary.get("licenses", {})
    row = 3
    for label, count, col_hex in [
        ("✅ Valid / Active", lic.get("valid", 0),    C["grn"]),
        ("⚠️ Expiring Soon", lic.get("expiring", 0), C["amb"]),
        ("🔴 Expired",       lic.get("expired", 0),  C["red"]),
    ]:
        ws3.cell(row=row,   column=1, value=label).font = bold(11, C["navy"])
        c = ws3.cell(row=row+1, column=1, value=count)
        c.font = bold(22, col_hex)
        c.alignment = center()
        row += 3

    row += 1
    ws3.merge_cells(f"A{row}:F{row}")
    ws3[f"A{row}"] = "📋 EXPIRING LICENSES (next 30 days)"
    ws3[f"A{row}"].font = bold(11, C["navy"])
    row += 1

    hds = ["License Name","Type","Expiry Date","Days Left","Status","Assigned To"]
    for col, h in enumerate(hds, 1):
        ws3.cell(row=row, column=col, value=h)
    style_header_row(ws3, row, 6)
    row += 1

    for l in (lic.get("expiring_list") or []):
        ws3.cell(row=row, column=1, value=l.get("license_name","—")).font = bold(10)
        ws3.cell(row=row, column=2, value=l.get("license_type","—"))
        ws3.cell(row=row, column=3, value=str(l.get("current_expiry_date") or "—"))
        days = l.get("days_to_expiry")
        c_d  = ws3.cell(row=row, column=4, value=days)
        if days is not None:
            c_d.font = Font(size=10, bold=True,
                color=C["red"] if days <= 7 else C["amb"] if days <= 30 else C["grn"])
        ws3.cell(row=row, column=5, value=l.get("status","—"))
        ws3.cell(row=row, column=6, value=l.get("assigned_to","—"))
        for col in range(1, 7):
            ws3.cell(row=row, column=col).border = thin_border()
        row += 1

    # ── Sheet 4: GRC Summary ──────────────────────────────────────────────────
    ws4 = wb.create_sheet("GRC Summary")
    ws4.column_dimensions["A"].width = 28
    ws4.column_dimensions["B"].width = 16
    ws4.column_dimensions["C"].width = 22
    ws4.column_dimensions["D"].width = 20

    ws4.merge_cells("A1:D1")
    ws4["A1"] = f"📊  GRC Domain Summary — {company}  |  {fiscal_month}"
    ws4["A1"].font = bold(13, C["navy"])
    ws4["A1"].fill = cell_fill(C["sky_lt"])
    ws4["A1"].alignment = center()

    grc_items = [
        ("Corporate Governance", v3.get("corporate",{}).get("non_compliant",0), "registers non-compliant"),
        ("Contract Compliance",  v3.get("contracts",{}).get("material_breach",0), "material breaches"),
        ("NDPR / Data Protection", v3.get("ndpr",{}).get("open_breaches",0), "open data breaches"),
        ("AML & KYC",            v3.get("aml",{}).get("high_risk",0), "high-risk parties"),
        ("Labour & Employment",  v3.get("labour",{}).get("expired_permits",0), "expired permits"),
        ("Environmental & HSE",  v3.get("environmental",{}).get("expired",0), "expired env. permits"),
        ("Industry Regulatory",  v3.get("industry",{}).get("overdue",0), "returns overdue"),
        ("Anti-Fraud & Integrity", v3.get("fraud",{}).get("under_investigation",0), "under investigation"),
        ("Training & Competency", f"{v3.get('training',{}).get('mandatory_pct',0):.0f}%", "mandatory completion"),
    ]

    row = 3
    hds = ["Domain","Issues / Score","Detail","Action Required"]
    for col, h in enumerate(hds, 1):
        ws4.cell(row=row, column=col, value=h)
    style_header_row(ws4, row, 4)
    row += 1

    for domain, issues, detail in grc_items:
        issues_v = issues if isinstance(issues, str) else int(issues)
        action   = "✅ No action" if issues_v == 0 or issues_v == "100%" else "⚠️ Review required"
        ws4.cell(row=row, column=1, value=domain).font = bold(10)
        c_iss = ws4.cell(row=row, column=2, value=issues_v)
        c_iss.alignment = center()
        if isinstance(issues_v, int) and issues_v > 0:
            c_iss.font = bold(10, C["red"])
            c_iss.fill = cell_fill(C["red_lt"])
        ws4.cell(row=row, column=3, value=detail)
        ws4.cell(row=row, column=4, value=action)
        for col in range(1, 5):
            ws4.cell(row=row, column=col).border = thin_border()
        row += 1

    # Finalise
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return {
        "success":      True,
        "file_data":    base64.b64encode(output.getvalue()).decode(),
        "file_name":    f"ComplianceHQ_{company}_{fiscal_month}.xlsx",
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }


@frappe.whitelist()
def download_compliance_report(company, fiscal_month=None):
    """Save report to Frappe file storage and return URL."""
    result = export_compliance_report(company, fiscal_month)
    if not result.get("success"):
        frappe.throw(_("Report generation failed: ") + result.get("error", ""))

    from frappe.utils.file_manager import save_file
    file_doc = save_file(
        fname=result["file_name"],
        content=base64.b64decode(result["file_data"]),
        dt="File", dn="Compliance Report",
        folder="Home/Reports", decode=False, is_private=0,
    )
    return {"success": True, "file_url": file_doc.file_url,
            "file_name": result["file_name"]}