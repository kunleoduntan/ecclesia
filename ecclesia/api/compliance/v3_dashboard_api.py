# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/compliance/v3_dashboard_api.py
"""
ComplianceHQ v3 — Domain Tab API
All whitelisted methods for the 9 new compliance domain dashboard tabs.
Called from compliance_hq_v3.js page.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate, date_diff, add_days


# ── Master summary (all domains, one call) ────────────────────────────────────

@frappe.whitelist()
def get_v3_domain_summary(company):
    """
    Single call that returns KPI data for ALL 9 new domains.
    Called on dashboard load to populate tab badges and overview cards.
    """
    return {
        "corporate":     _corporate_summary(company),
        "contracts":     _contracts_summary(company),
        "ndpr":          _ndpr_summary(company),
        "aml":           _aml_summary(company),
        "labour":        _labour_summary(company),
        "environmental": _environmental_summary(company),
        "industry":      _industry_summary(company),
        "fraud":         _fraud_summary(company),
        "training":      _training_summary(company),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 1: CORPORATE GOVERNANCE
# ═══════════════════════════════════════════════════════════════════════════════

def _corporate_summary(company):
    registers = frappe.db.get_all(
        "Corporate Compliance Register",
        filters={"company": company},
        fields=["name", "fiscal_year", "overall_status", "annual_return_status",
                "annual_return_due_date", "annual_return_filed_date",
                "next_agm_due_date", "agm_held_on_time", "statutory_registers_current"]
    )
    resolutions = frappe.db.get_all(
        "Board Resolution",
        filters={"company": company, "docstatus": 1},
        fields=["implementation_status", "cac_filing_required", "cac_filed"]
    )
    return {
        "total_registers":        len(registers),
        "non_compliant":          sum(1 for r in registers if r.overall_status == "Non-Compliant"),
        "annual_return_overdue":  sum(1 for r in registers if r.annual_return_status == "Overdue"),
        "agm_missed":             sum(1 for r in registers if not r.agm_held_on_time),
        "resolutions_pending":    sum(1 for r in resolutions if r.implementation_status == "Pending"),
        "cac_filings_outstanding":sum(1 for r in resolutions if r.cac_filing_required and not r.cac_filed),
        "registers":              registers,
        "resolutions":            resolutions[:10],
    }


@frappe.whitelist()
def get_corporate_governance_tab(company):
    summary = _corporate_summary(company)
    entries = frappe.db.sql("""
        SELECT register_type, COUNT(*) as count,
               SUM(CASE WHEN cac_form_filed=1 THEN 1 ELSE 0 END) as filed,
               SUM(CASE WHEN cac_form_filed=0 THEN 1 ELSE 0 END) as unfiled
        FROM `tabStatutory Register Entry`
        WHERE company = %s
        GROUP BY register_type
        ORDER BY count DESC
    """, (company,), as_dict=True)
    pending_resolutions = frappe.db.get_all(
        "Board Resolution",
        filters={"company": company, "docstatus": 1, "implementation_status": ["!=", "Implemented"]},
        fields=["name", "resolution_number", "meeting_type", "meeting_date",
                "resolution_category", "implementation_status", "cac_filing_required", "cac_filed"],
        order_by="meeting_date desc",
        limit=20
    )
    return {**summary, "register_entries_by_type": entries, "pending_resolutions": pending_resolutions}


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 2: CONTRACT COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════════════

def _contracts_summary(company):
    contracts = frappe.db.get_all(
        "Contract Compliance Record",
        filters={"company": company},
        fields=["name", "compliance_title", "vendor", "compliance_status",
                "sla_compliance_pct", "open_breaches", "contract_end", "contract_value"]
    )
    return {
        "total":             len(contracts),
        "compliant":         sum(1 for c in contracts if c.compliance_status == "Compliant"),
        "minor_breach":      sum(1 for c in contracts if c.compliance_status == "Minor Breach"),
        "material_breach":   sum(1 for c in contracts if c.compliance_status == "Material Breach"),
        "termination_risk":  sum(1 for c in contracts if c.compliance_status == "Termination Risk"),
        "expired":           sum(1 for c in contracts if c.compliance_status == "Expired"),
        "avg_sla":           round(sum(flt(c.sla_compliance_pct) for c in contracts) / len(contracts), 1) if contracts else 0,
        "total_open_breaches": sum(int(c.open_breaches or 0) for c in contracts),
        "records":           contracts,
    }


@frappe.whitelist()
def get_contracts_tab(company):
    summary = _contracts_summary(company)
    expiring_60 = frappe.db.get_all(
        "Contract Compliance Record",
        filters={"company": company,
                 "contract_end": ["between", [nowdate(), add_days(nowdate(), 60)]],
                 "compliance_status": ["!=", "Expired"]},
        fields=["name", "compliance_title", "vendor", "contract_end",
                "compliance_status", "contract_value", "sla_compliance_pct"],
        order_by="contract_end asc"
    )
    return {**summary, "expiring_60_days": expiring_60}


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 3: NDPR / DATA PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════

def _ndpr_summary(company):
    records = frappe.db.get_all(
        "Data Processing Record",
        filters={"company": company},
        fields=["name", "status", "is_sensitive_data", "privacy_impact_done",
                "nitda_registered", "next_review_date"]
    )
    breaches = frappe.db.get_all(
        "Data Breach Register",
        filters={"company": company},
        fields=["name", "severity", "status", "nitda_notified",
                "late_notification_flag", "breach_date"]
    )
    overdue_reviews = [r for r in records
                       if r.next_review_date and getdate(r.next_review_date) < getdate(nowdate())]
    return {
        "processing_records":    len(records),
        "active_records":        sum(1 for r in records if r.status == "Active"),
        "sensitive_data_records":sum(1 for r in records if r.is_sensitive_data),
        "dpia_missing":          sum(1 for r in records if r.is_sensitive_data and not r.privacy_impact_done),
        "nitda_registered":      sum(1 for r in records if r.nitda_registered),
        "overdue_reviews":       len(overdue_reviews),
        "total_breaches":        len(breaches),
        "open_breaches":         sum(1 for b in breaches if b.status not in ("Remediated","Closed")),
        "late_notifications":    sum(1 for b in breaches if b.late_notification_flag),
        "breaches":              breaches,
    }


@frappe.whitelist()
def get_ndpr_tab(company):
    summary = _ndpr_summary(company)
    reviews_due = frappe.db.get_all(
        "Data Processing Record",
        filters={"company": company, "status": "Active",
                 "next_review_date": ["<=", add_days(nowdate(), 30)]},
        fields=["name","processing_title","legal_basis","is_sensitive_data",
                "privacy_impact_done","next_review_date","dpo"],
        order_by="next_review_date asc"
    )
    open_breaches = frappe.db.get_all(
        "Data Breach Register",
        filters={"company": company, "status": ["not in", ["Remediated","Closed"]]},
        fields=["name","breach_title","severity","status","breach_date",
                "data_subjects_affected","nitda_notified","late_notification_flag"],
        order_by="breach_date desc"
    )
    return {**summary, "reviews_due_30_days": reviews_due, "open_breaches_detail": open_breaches}


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 4: AML & KYC
# ═══════════════════════════════════════════════════════════════════════════════

def _aml_summary(company):
    kyc = frappe.db.get_all(
        "AML KYC Record",
        filters={"company": company, "docstatus": 1},
        fields=["risk_rating", "kyc_level", "kyc_expiry_date", "is_pep", "sanctions_match"]
    )
    strs = frappe.db.get_all(
        "Suspicious Transaction Report",
        filters={"company": company},
        fields=["status","nfiu_submitted","report_type"]
    )
    expiring_kyc = [r for r in kyc if r.kyc_expiry_date and
                    0 <= date_diff(r.kyc_expiry_date, nowdate()) <= 30]
    return {
        "total_kyc":         len(kyc),
        "high_risk":         sum(1 for r in kyc if r.risk_rating in ("High","PEP — High")),
        "pep_count":         sum(1 for r in kyc if r.is_pep),
        "sanctions_match":   sum(1 for r in kyc if r.sanctions_match),
        "kyc_expiring_30d":  len(expiring_kyc),
        "total_strs":        len(strs),
        "strs_pending_nfiu": sum(1 for s in strs if not s.nfiu_submitted),
        "strs_submitted":    sum(1 for s in strs if s.nfiu_submitted),
    }


@frappe.whitelist()
def get_aml_tab(company):
    summary = _aml_summary(company)
    high_risk = frappe.db.get_all(
        "AML KYC Record",
        filters={"company": company, "docstatus": 1,
                 "risk_rating": ["in", ["High","PEP — High","Sanctioned — Blocked"]]},
        fields=["name","party_name_display","party_type","risk_rating",
                "kyc_expiry_date","sanctions_match","is_pep","kyc_level"],
        order_by="risk_rating desc",
        limit=20
    )
    pending_strs = frappe.db.get_all(
        "Suspicious Transaction Report",
        filters={"company": company, "nfiu_submitted": 0,
                 "status": ["not in", ["Closed — No Action"]]},
        fields=["name","str_title","report_type","transaction_date",
                "transaction_amount","party_name","status"],
        order_by="transaction_date desc",
        limit=10
    )
    risk_dist = frappe.db.sql("""
        SELECT risk_rating, COUNT(*) as count
        FROM `tabAML KYC Record`
        WHERE company=%s AND docstatus=1
        GROUP BY risk_rating
    """, (company,), as_dict=True)
    return {**summary, "high_risk_parties": high_risk,
            "pending_nfiu_strs": pending_strs, "risk_distribution": risk_dist}


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 5: LABOUR & EMPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════════

def _labour_summary(company):
    trackers = frappe.db.get_all(
        "Labour Compliance Tracker",
        filters={"company": company, "docstatus": 1},
        fields=["period_label","overall_status","minimum_wage_compliant",
                "pencom_all_registered","working_hours_compliant"],
        order_by="period_label desc",
        limit=12
    )
    permits = frappe.db.get_all(
        "Expatriate Permit Register",
        filters={"company": company},
        fields=["status","days_to_expiry","permit_type"]
    )
    latest = trackers[0] if trackers else {}
    return {
        "latest_period":      latest.get("period_label","—"),
        "latest_status":      latest.get("overall_status","No Data"),
        "wage_compliant":     latest.get("minimum_wage_compliant", None),
        "pencom_compliant":   latest.get("pencom_all_registered", None),
        "total_permits":      len(permits),
        "expired_permits":    sum(1 for p in permits if p.status == "Expired"),
        "expiring_permits":   sum(1 for p in permits if p.status == "Expiring Soon"),
        "non_compliant_months": sum(1 for t in trackers if t.overall_status == "Non-Compliant"),
        "trend":              trackers,
    }


@frappe.whitelist()
def get_labour_tab(company):
    summary = _labour_summary(company)
    expiring_permits = frappe.db.get_all(
        "Expatriate Permit Register",
        filters={"company": company,
                 "status": ["in", ["Active","Expiring Soon"]],
                 "expiry_date": ["<=", add_days(nowdate(), 90)]},
        fields=["name","permit_title","employee","permit_type",
                "expiry_date","days_to_expiry","status","renewal_cost"],
        order_by="expiry_date asc"
    )
    labour_trend = frappe.db.get_all(
        "Labour Compliance Tracker",
        filters={"company": company, "docstatus": 1},
        fields=["period_label","overall_status","minimum_wage_compliant",
                "working_hours_compliant","pencom_all_registered",
                "nhf_all_registered","employment_contracts_compliant","total_employees"],
        order_by="period_label desc",
        limit=12
    )
    return {**summary, "expiring_permits": expiring_permits, "labour_trend": labour_trend}


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 6: ENVIRONMENTAL & HSE
# ═══════════════════════════════════════════════════════════════════════════════

def _environmental_summary(company):
    records = frappe.db.get_all(
        "Environmental Compliance Record",
        filters={"company": company},
        fields=["name","status","permit_type","expiry_date","days_to_expiry",
                "corrective_actions_pending","last_inspection_result"]
    )
    return {
        "total":              len(records),
        "active":             sum(1 for r in records if r.status == "Active"),
        "expiring_soon":      sum(1 for r in records if r.status == "Expiring Soon"),
        "expired":            sum(1 for r in records if r.status == "Expired"),
        "pending_actions":    sum(int(r.corrective_actions_pending or 0) for r in records),
        "major_non_compliance": sum(1 for r in records if r.last_inspection_result == "Major Non-Compliance"),
        "records":            records,
    }


@frappe.whitelist()
def get_environmental_tab(company):
    summary = _environmental_summary(company)
    expiring = frappe.db.get_all(
        "Environmental Compliance Record",
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
    return {**summary, "expiring_90_days": expiring, "by_permit_type": by_type}


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 7: INDUSTRY REGULATORY RETURNS
# ═══════════════════════════════════════════════════════════════════════════════

def _industry_summary(company):
    returns = frappe.db.get_all(
        "Regulatory Return",
        filters={"company": company},
        fields=["name","authority","status","due_date","late_flag","penalty_incurred",
                "industry_category","return_type"]
    )
    total_penalty = sum(flt(r.penalty_incurred or 0) for r in returns)
    return {
        "total":         len(returns),
        "pending":       sum(1 for r in returns if r.status in ("Pending","Preparing")),
        "overdue":       sum(1 for r in returns if r.status == "Overdue"),
        "late":          sum(1 for r in returns if r.late_flag),
        "submitted":     sum(1 for r in returns if r.status in ("Submitted","Late Submitted","Accepted")),
        "total_penalty": total_penalty,
        "records":       returns,
    }


@frappe.whitelist()
def get_industry_tab(company):
    summary = _industry_summary(company)
    overdue = frappe.db.get_all(
        "Regulatory Return",
        filters={"company": company, "status": ["in", ["Pending","Overdue","Preparing"]]},
        fields=["name","return_title","authority","return_type","period_covered",
                "due_date","status","late_flag","penalty_for_non_filing","filed_by"],
        order_by="due_date asc",
        limit=20
    )
    by_authority = frappe.db.sql("""
        SELECT authority, COUNT(*) as total,
               SUM(CASE WHEN status='Overdue' THEN 1 ELSE 0 END) as overdue,
               SUM(CASE WHEN late_flag=1 THEN 1 ELSE 0 END) as late
        FROM `tabRegulatory Return`
        WHERE company=%s GROUP BY authority ORDER BY total DESC
    """, (company,), as_dict=True)
    return {**summary, "overdue_returns": overdue, "by_authority": by_authority}


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 8: ANTI-FRAUD & INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════════

def _fraud_summary(company):
    reports = frappe.db.get_all(
        "Whistleblower Report",
        filters={"company": company},
        fields=["status","severity","report_category","outcome","escalated_to_board"]
    )
    coi = frappe.db.get_all(
        "Conflict of Interest Declaration",
        filters={"company": company},
        fields=["has_conflict","approval_status","fiscal_year"]
    )
    return {
        "total_wb_reports":       len(reports),
        "under_investigation":    sum(1 for r in reports if r.status == "Under Investigation"),
        "escalated":              sum(1 for r in reports if r.status == "Escalated"),
        "substantiated":          sum(1 for r in reports if r.outcome and "Substantiated — Action" in (r.outcome or "")),
        "critical_reports":       sum(1 for r in reports if r.severity == "Critical"),
        "board_escalations":      sum(1 for r in reports if r.escalated_to_board),
        "total_coi":              len(coi),
        "conflicts_declared":     sum(1 for c in coi if c.has_conflict),
        "coi_pending_review":     sum(1 for c in coi if c.approval_status == "Pending"),
    }


@frappe.whitelist()
def get_fraud_tab(company):
    summary = _fraud_summary(company)
    open_reports = frappe.db.get_all(
        "Whistleblower Report",
        filters={"company": company,
                 "status": ["in", ["Received","Under Investigation","Escalated"]]},
        fields=["name","report_code","received_date","channel","report_category",
                "severity","status","assigned_investigator","estimated_financial_impact"],
        order_by="received_date desc",
        limit=15
    )
    pending_coi = frappe.db.get_all(
        "Conflict of Interest Declaration",
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
    return {**summary, "open_reports": open_reports,
            "pending_coi_reviews": pending_coi, "by_category": by_category}


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN 9: TRAINING & COMPETENCY
# ═══════════════════════════════════════════════════════════════════════════════

def _training_summary(company):
    records = frappe.db.get_all(
        "Compliance Training Record",
        filters={"company": company, "docstatus": 1},
        fields=["completion_status","training_category","is_mandatory","passed","employee"]
    )
    calendars = frappe.db.get_all(
        "Compliance Training Calendar",
        filters={"company": company, "docstatus": 1},
        fields=["status","training_category","actual_completion_pct",
                "completion_target_pct","scheduled_date"]
    )
    mandatory = [r for r in records if r.is_mandatory]
    m_completed = sum(1 for r in mandatory if r.completion_status == "Completed")
    return {
        "total_records":       len(records),
        "mandatory_total":     len(mandatory),
        "mandatory_completed": m_completed,
        "mandatory_pct":       round(m_completed / len(mandatory) * 100, 1) if mandatory else 0,
        "failed":              sum(1 for r in records if r.completion_status == "Failed"),
        "unique_employees":    len(set(r.employee for r in records)),
        "upcoming_sessions":   sum(1 for c in calendars if c.status in ("Planned","Scheduled")),
        "below_target":        sum(1 for c in calendars if
                                   flt(c.actual_completion_pct) < flt(c.completion_target_pct)),
    }


@frappe.whitelist()
def get_training_tab(company, fiscal_year=None):
    summary = _training_summary(company)
    by_category = frappe.db.sql("""
        SELECT training_category,
               COUNT(*) as total,
               SUM(CASE WHEN completion_status='Completed' AND is_mandatory=1 THEN 1 ELSE 0 END) as completed,
               SUM(CASE WHEN is_mandatory=1 THEN 1 ELSE 0 END) as mandatory,
               SUM(CASE WHEN completion_status='Failed' THEN 1 ELSE 0 END) as failed
        FROM `tabCompliance Training Record`
        WHERE company=%s AND docstatus=1
        GROUP BY training_category ORDER BY mandatory DESC
    """, (company,), as_dict=True)
    upcoming = frappe.db.get_all(
        "Compliance Training Calendar",
        filters={"company": company, "docstatus": 1,
                 "status": ["in", ["Planned","Scheduled"]],
                 "scheduled_date": [">=", nowdate()]},
        fields=["name","calendar_title","training_category","scheduled_date",
                "target_headcount","actual_attendees","actual_completion_pct",
                "completion_target_pct","is_mandatory","venue"],
        order_by="scheduled_date asc",
        limit=10
    )
    overdue_employees = frappe.db.sql("""
        SELECT e.employee_name, e.department, r.training_category,
               r.certificate_expiry, r.completion_status
        FROM `tabCompliance Training Record` r
        JOIN `tabEmployee` e ON e.name = r.employee
        WHERE r.company=%s AND r.is_mandatory=1 AND r.docstatus=1
          AND (r.completion_status = 'Failed'
            OR (r.certificate_expiry IS NOT NULL AND r.certificate_expiry < CURDATE()))
        LIMIT 20
    """, (company,), as_dict=True)
    return {**summary, "by_category": by_category,
            "upcoming_sessions": upcoming, "overdue_employees": overdue_employees}


# ═══════════════════════════════════════════════════════════════════════════════
#  CROSS-DOMAIN SCORE
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_full_compliance_score(company):
    """
    Holistic compliance score across all 9 v3 domains.
    Returns a score per domain and an overall weighted score.
    """
    v3 = get_v3_domain_summary(company)

    def pct(ok, total):
        return round(ok / total * 100, 1) if total else 100.0

    scores = {
        "corporate":     pct(
            v3["corporate"]["total_registers"] - v3["corporate"]["non_compliant"],
            max(v3["corporate"]["total_registers"], 1)
        ),
        "contracts":     pct(v3["contracts"]["compliant"], max(v3["contracts"]["total"], 1)),
        "ndpr":          pct(
            v3["ndpr"]["processing_records"] - v3["ndpr"]["dpia_missing"],
            max(v3["ndpr"]["processing_records"], 1)
        ),
        "aml":           100.0 if v3["aml"]["total_kyc"] == 0 else pct(
            v3["aml"]["total_kyc"] - v3["aml"]["kyc_expiring_30d"],
            v3["aml"]["total_kyc"]
        ),
        "labour":        100.0 if v3["labour"]["latest_status"] == "Compliant"
                         else 75.0 if v3["labour"]["latest_status"] == "Minor Issues"
                         else 50.0 if v3["labour"]["latest_status"] == "Major Issues"
                         else 25.0,
        "environmental": pct(v3["environmental"]["active"], max(v3["environmental"]["total"], 1)),
        "industry":      pct(v3["industry"]["submitted"], max(v3["industry"]["total"], 1)),
        "fraud":         100.0 if v3["fraud"]["total_wb_reports"] == 0
                         else pct(
            v3["fraud"]["total_wb_reports"] - v3["fraud"]["under_investigation"],
            v3["fraud"]["total_wb_reports"]
        ),
        "training":      v3["training"]["mandatory_pct"],
    }

    weights = {
        "corporate": 0.10, "contracts": 0.08, "ndpr": 0.12,
        "aml": 0.15,       "labour": 0.12,    "environmental": 0.10,
        "industry": 0.10,  "fraud": 0.08,     "training": 0.05,
    }
    overall = sum(scores[k] * weights[k] for k in scores)

    return {
        "domain_scores": scores,
        "overall_v3":    round(overall, 1),
        "weights":       weights,
    }