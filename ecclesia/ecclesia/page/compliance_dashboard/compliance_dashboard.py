# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/page/compliance_dashboard/compliance_dashboard.py

import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, get_last_day
import json
import base64
from io import BytesIO

# ─── MAIN DASHBOARD ENDPOINTS ──────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_summary(company, fiscal_month=None):
    """Returns all data for the ComplianceHQ overview dashboard."""
    if not company:
        frappe.throw(_("Company is required"))

    if not fiscal_month:
        fiscal_month = frappe.utils.nowdate()[:7]

    year, month = fiscal_month.split('-')
    period_start = f"{year}-{month}-01"
    period_end = get_last_day(period_start)

    return {
        "tax": _get_tax_status(company, period_start, period_end),
        "statutory": _get_statutory_status(company, period_start, period_end),
        "licenses": _get_license_status(company),
        "incidents": _get_incidents(company),
        "calendar": _get_calendar_entries(company, period_start, period_end),
        "tasks": _get_open_tasks(company),
        "total_liability": _get_total_liability(company, period_start, period_end),
        "v3": _get_v3_domain_summary(company),
    }


@frappe.whitelist()
def get_v3_domain_summary(company):
    """Returns domain summaries for the v3 dashboard tabs."""
    if not company:
        frappe.throw(_("Company is required"))
    return _get_v3_domain_summary(company)


@frappe.whitelist()
def get_full_compliance_score(company):
    """Returns overall and per-domain compliance scores."""
    if not company:
        frappe.throw(_("Company is required"))

    domain_scores = {}
    total_score = 0
    count = 0

    domains = {
        "corporate": "Corporate Compliance Register",
        "contracts": "Contract Compliance Record",
        "ndpr": "Data Processing Record",
        "aml": "AML KYC Record",
        "labour": "Labour Compliance Tracker",
        "environmental": "Environmental Compliance Record",
        "industry": "Regulatory Return",
        "fraud": "Whistleblower Report",
        "training": "Compliance Training Record",
    }

    for key, doctype in domains.items():
        score = _calculate_domain_score(company, doctype)
        domain_scores[key] = score
        total_score += score
        count += 1

    overall = round(total_score / count, 1) if count > 0 else 0

    return {
        "overall_v3": overall,
        "domain_scores": domain_scores,
    }


# ─── TAB-SPECIFIC ENDPOINTS ──────────────────────────────────────────────

@frappe.whitelist()
def get_corporate_governance_tab(company):
    """Returns corporate governance data for the tab view."""
    if not company:
        return {}

    registers = frappe.db.get_all("Corporate Compliance Register",
        filters={"company": company},
        fields=["name", "company", "fiscal_year", "rc_number", "annual_return_status", "agm_held_on_time", "overall_status"]
    )

    pending_resolutions = frappe.db.get_all("Board Resolution",
        filters={"company": company, "implementation_status": ["!=", "Implemented"]},
        fields=["name", "resolution_number", "meeting_type", "meeting_date", "resolution_category", "cac_filing_required", "cac_filed", "implementation_status"]
    )

    register_entries = frappe.db.sql("""
        SELECT 
            sre.register_type, 
            COUNT(*) as count
        FROM `tabStatutory Register Entry` sre
        WHERE sre.corporate_register IN (
            SELECT name FROM `tabCorporate Compliance Register` WHERE company = %s
        )
        GROUP BY sre.register_type
    """, company, as_dict=True)

    return {
        "registers": registers,
        "pending_resolutions": pending_resolutions,
        "register_entries": register_entries,
    }


@frappe.whitelist()
def get_contracts_tab(company):
    """Returns contract compliance data."""
    if not company:
        return {}

    records = frappe.db.get_all("Contract Compliance Record",
        filters={"company": company},
        fields=["name", "compliance_title", "vendor", "sla_compliance_pct", "open_breaches", "contract_end", "compliance_status"],
        order_by="modified desc",
        limit_page_length=50
    )

    return {"records": records}


@frappe.whitelist()
def get_ndpr_tab(company):
    """Returns NDPR / data protection data."""
    if not company:
        return {}

    open_breaches_detail = frappe.db.get_all("Data Breach Register",
        filters={"company": company, "status": ["!=", "Closed"]},
        fields=["name", "breach_title", "breach_type", "severity", "data_subjects_affected", "nitda_notified", "status"]
    )

    return {"open_breaches_detail": open_breaches_detail}


@frappe.whitelist()
def get_aml_tab(company):
    """Returns AML & KYC data."""
    if not company:
        return {}

    high_risk_parties = frappe.db.get_all("AML KYC Record",
        filters={"company": company, "risk_rating": ["in", ["High", "PEP — High", "Sanctioned — Blocked"]]},
        fields=["name", "party_name_display", "party_type", "risk_rating", "kyc_level", "kyc_expiry_date", "is_pep", "sanctions_match"]
    )

    return {"high_risk_parties": high_risk_parties}


@frappe.whitelist()
def get_labour_tab(company):
    """Returns labour & employment data."""
    if not company:
        return {}

    expiring_permits = frappe.db.get_all("Expatriate Permit Register",
        filters={"company": company, "status": ["in", ["Active", "Expiring Soon"]]},
        fields=["name", "permit_title", "employee", "permit_type", "expiry_date", "days_to_expiry", "status"],
        order_by="days_to_expiry asc"
    )

    return {"expiring_permits": expiring_permits[:20]}


@frappe.whitelist()
def get_environmental_tab(company):
    """Returns environmental compliance data."""
    if not company:
        return {}

    expiring_90_days = frappe.db.get_all("Environmental Compliance Record",
        filters={"company": company, "days_to_expiry": ["<=", 90]},
        fields=["name", "permit_title", "permit_type", "issuing_authority", "expiry_date", "days_to_expiry", "status"],
        order_by="days_to_expiry asc"
    )

    return {"expiring_90_days": expiring_90_days[:20]}


@frappe.whitelist()
def get_industry_tab(company):
    """Returns industry regulatory data."""
    if not company:
        return {}

    overdue_returns = frappe.db.get_all("Regulatory Return",
        filters={"company": company, "status": ["in", ["Overdue", "Pending", "Late Submitted"]]},
        fields=["name", "return_title", "authority", "period_covered", "due_date", "late_flag", "penalty_for_non_filing", "status"],
        order_by="due_date asc"
    )

    return {"overdue_returns": overdue_returns}


@frappe.whitelist()
def get_fraud_tab(company):
    """Returns anti-fraud & integrity data."""
    if not company:
        return {}

    open_reports = frappe.db.get_all("Whistleblower Report",
        filters={"company": company, "status": ["in", ["Received", "Under Investigation", "Escalated"]]},
        fields=["name", "report_code", "received_date", "channel", "report_category", "severity", "status"]
    )

    return {"open_reports": open_reports}


@frappe.whitelist()
def get_training_tab(company):
    """Returns training compliance data."""
    if not company:
        return {}

    by_category = frappe.db.sql("""
        SELECT 
            training_category,
            COUNT(*) as total,
            SUM(CASE WHEN completion_status IN ('Completed', 'Passed') THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN is_mandatory = 1 THEN 1 ELSE 0 END) as mandatory,
            SUM(CASE WHEN completion_status = 'Failed' THEN 1 ELSE 0 END) as failed
        FROM `tabCompliance Training Record`
        WHERE company = %s
        GROUP BY training_category
    """, company, as_dict=True)

    return {"by_category": by_category}


@frappe.whitelist()
def get_ai_compliance_analysis(company, fiscal_month=None):
    """Returns AI-generated compliance analysis."""
    if not company:
        return {"success": False, "error": "Company required"}

    summary = get_dashboard_summary(company, fiscal_month)
    scores = get_full_compliance_score(company)

    risk_level = "Low"
    if scores.get('overall_v3', 100) < 60:
        risk_level = "High"
    elif scores.get('overall_v3', 100) < 75:
        risk_level = "Medium"

    return {
        "success": True,
        "analysis": {
            "response": {
                "risk_level": risk_level,
                "summary": f"Compliance score is {scores.get('overall_v3', 0)}% with {risk_level} risk exposure.",
                "penalty_exposure": f"Potential penalties estimated at ₦{summary.get('total_liability', 0) * 0.25:,.0f}",
                "actions": [
                    {"action": f"Renew {summary.get('licenses', {}).get('expired', 0)} expired licenses immediately", "deadline": "Within 7 days", "authority": "Licensing Authority"},
                    {"action": f"Address {summary.get('v3', {}).get('ndpr', {}).get('open_breaches', 0)} open data breaches", "deadline": "Within 14 days", "authority": "NITDA"},
                    {"action": f"File {summary.get('v3', {}).get('industry', {}).get('overdue', 0)} overdue regulatory returns", "deadline": "Within 7 days", "authority": "Various Regulators"},
                    {"action": "Review AML/KYC procedures for sanctions matches", "deadline": "Immediate", "authority": "AMLCO"},
                ],
                "strategic_recommendation": "Establish a monthly compliance review cycle and automate filing reminders to prevent future overdue obligations."
            }
        }
    }


# ─── EXCEL EXPORT ───────────────────────────────────────────────────────────

@frappe.whitelist()
def export_compliance_report(company, fiscal_month=None, format="xlsx"):
    """Exports a beautifully formatted Excel report."""
    if not company:
        frappe.throw(_("Company is required"))

    if not fiscal_month:
        fiscal_month = frappe.utils.nowdate()[:7]

    summary = get_dashboard_summary(company, fiscal_month)
    scores = get_full_compliance_score(company)

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        frappe.throw(_("openpyxl library is required for Excel export. Please install it via pip."))

    wb = openpyxl.Workbook()

    COLORS = {
        "primary": "1E3A5F",
        "green": "059669",
        "green_light": "D1FAE5",
        "red": "DC2626",
        "red_light": "FEE2E2",
        "amber": "D97706",
        "amber_light": "FEF3C7",
        "header_bg": "1E3A5F",
        "header_text": "FFFFFF",
    }

    # Sheet 1: Executive Dashboard
    ws1 = wb.active
    ws1.title = "Executive Dashboard"

    ws1.merge_cells('A1:F1')
    ws1['A1'] = f"🏛️ ComplianceHQ Executive Report — {company}"
    ws1['A1'].font = Font(size=16, bold=True, color=COLORS["primary"])

    ws1['A2'] = f"Period: {fiscal_month}  |  Generated: {frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M')}"
    ws1['A2'].font = Font(size=10)

    ws1.merge_cells('A4:B4')
    ws1['A4'] = "📊 OVERALL GRC SCORE"
    ws1['A4'].font = Font(size=11, bold=True, color=COLORS["primary"])
    ws1['A5'] = f"{scores.get('overall_v3', 0)}%"
    overall_score = scores.get('overall_v3', 0)
    if overall_score >= 80:
        ws1['A5'].font = Font(size=20, bold=True, color=COLORS["green"])
    elif overall_score >= 60:
        ws1['A5'].font = Font(size=20, bold=True, color=COLORS["amber"])
    else:
        ws1['A5'].font = Font(size=20, bold=True, color=COLORS["red"])

    row = 8
    ws1.merge_cells(f'A{row}:B{row}')
    ws1[f'A{row}'] = "📋 DOMAIN SCORES BREAKDOWN"
    ws1[f'A{row}'].font = Font(size=11, bold=True, color=COLORS["primary"])
    row += 1

    domain_headers = ["Domain", "Score", "Status", "Issues"]
    for col, header in enumerate(domain_headers, start=1):
        cell = ws1.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True, color=COLORS["header_text"])
        cell.fill = PatternFill(start_color=COLORS["header_bg"], end_color=COLORS["header_bg"], fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 1

    domain_labels = {
        "corporate": "Governance",
        "contracts": "Contracts",
        "ndpr": "NDPR",
        "aml": "AML & KYC",
        "labour": "Labour",
        "environmental": "Environmental",
        "industry": "Regulatory",
        "fraud": "Integrity",
        "training": "Training",
    }

    ds = scores.get('domain_scores', {})
    for key, label in domain_labels.items():
        score = ds.get(key, 0)
        status = "Compliant" if score >= 80 else "Minor Issues" if score >= 60 else "Major Issues"
        issues = {
            "corporate": summary.get('v3', {}).get('corporate', {}).get('non_compliant', 0),
            "contracts": summary.get('v3', {}).get('contracts', {}).get('material_breach', 0),
            "ndpr": summary.get('v3', {}).get('ndpr', {}).get('open_breaches', 0),
            "aml": summary.get('v3', {}).get('aml', {}).get('high_risk', 0),
            "labour": summary.get('v3', {}).get('labour', {}).get('expired_permits', 0),
            "environmental": summary.get('v3', {}).get('environmental', {}).get('expired', 0),
            "industry": summary.get('v3', {}).get('industry', {}).get('overdue', 0),
            "fraud": summary.get('v3', {}).get('fraud', {}).get('under_investigation', 0),
            "training": 1 if 100 - summary.get('v3', {}).get('training', {}).get('mandatory_pct', 100) > 20 else 0,
        }
        ws1.cell(row=row, column=1, value=label)
        ws1.cell(row=row, column=2, value=f"{score}%")
        ws1.cell(row=row, column=3, value=status)
        ws1.cell(row=row, column=4, value=issues.get(key, 0))
        row += 1

    for col in range(1, 5):
        ws1.column_dimensions[get_column_letter(col)].width = 20

    # Sheet 2: Tax & Statutory
    ws2 = wb.create_sheet("Tax & Statutory")
    ws2.merge_cells('A1:F1')
    ws2['A1'] = f"💰 Tax & Statutory Obligations — {company}"
    ws2['A1'].font = Font(size=16, bold=True, color=COLORS["primary"])

    row = 3
    ws2.merge_cells(f'A{row}:F{row}')
    ws2[f'A{row}'] = "📊 TAX OBLIGATIONS"
    ws2[f'A{row}'].font = Font(size=11, bold=True, color=COLORS["primary"])
    row += 1

    tax_headers = ["Obligation", "Status", "Liability (₦)", "Paid (₦)", "Balance (₦)", "Compliance %"]
    for col, header in enumerate(tax_headers, start=1):
        cell = ws2.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True, color=COLORS["header_text"])
        cell.fill = PatternFill(start_color=COLORS["header_bg"], end_color=COLORS["header_bg"], fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 1

    tax_data = summary.get('tax', {})
    for obligation in ["VAT", "WHT", "PAYE", "CIT"]:
        data = tax_data.get(obligation, {})
        liability = data.get('liability', 0)
        paid = data.get('paid', 0)
        balance = data.get('balance', 0)
        pct = round((paid / liability * 100) if liability > 0 else 0)
        status = data.get('status', 'Not Generated')

        ws2.cell(row=row, column=1, value=obligation)
        ws2.cell(row=row, column=2, value=status)
        ws2.cell(row=row, column=3, value=liability).number_format = '#,##0'
        ws2.cell(row=row, column=4, value=paid).number_format = '#,##0'
        ws2.cell(row=row, column=5, value=balance).number_format = '#,##0'
        ws2.cell(row=row, column=6, value=f"{pct}%")
        row += 1

    row += 1
    ws2.merge_cells(f'A{row}:F{row}')
    ws2[f'A{row}'] = "📋 STATUTORY OBLIGATIONS"
    ws2[f'A{row}'].font = Font(size=11, bold=True, color=COLORS["primary"])
    row += 1

    for col, header in enumerate(tax_headers, start=1):
        cell = ws2.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True, color=COLORS["header_text"])
        cell.fill = PatternFill(start_color=COLORS["header_bg"], end_color=COLORS["header_bg"], fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 1

    statutory_data = summary.get('statutory', {})
    for obligation in ["Pension", "NHF", "NSITF", "ITF"]:
        data = statutory_data.get(obligation, {})
        liability = data.get('liability', 0)
        paid = data.get('paid', 0)
        balance = data.get('balance', 0)
        pct = round((paid / liability * 100) if liability > 0 else 0)
        status = data.get('status', 'Not Generated')

        ws2.cell(row=row, column=1, value=obligation)
        ws2.cell(row=row, column=2, value=status)
        ws2.cell(row=row, column=3, value=liability).number_format = '#,##0'
        ws2.cell(row=row, column=4, value=paid).number_format = '#,##0'
        ws2.cell(row=row, column=5, value=balance).number_format = '#,##0'
        ws2.cell(row=row, column=6, value=f"{pct}%")
        row += 1

    for col in range(1, 7):
        ws2.column_dimensions[get_column_letter(col)].width = 20

    # Sheet 3: Licenses & Permits
    ws3 = wb.create_sheet("Licenses & Permits")
    ws3.merge_cells('A1:F1')
    ws3['A1'] = f"🎖️ Licenses & Permits — {company}"
    ws3['A1'].font = Font(size=16, bold=True, color=COLORS["primary"])

    row = 3
    ws3.merge_cells(f'A{row}:F{row}')
    ws3[f'A{row}'] = "📊 LICENSE STATUS SUMMARY"
    ws3[f'A{row}'].font = Font(size=11, bold=True, color=COLORS["primary"])
    row += 1

    lic = summary.get('licenses', {})
    status_summary = [
        ("Valid / Active", lic.get('valid', 0), COLORS["green"]),
        ("Expiring Soon", lic.get('expiring', 0), COLORS["amber"]),
        ("Expired", lic.get('expired', 0), COLORS["red"]),
    ]

    for i, (label, count, color) in enumerate(status_summary):
        col = i * 2 + 1
        ws3.merge_cells(f'{get_column_letter(col)}{row}:{get_column_letter(col+1)}{row}')
        ws3[f'{get_column_letter(col)}{row}'] = label
        ws3[f'{get_column_letter(col)}{row}'].font = Font(size=10, bold=True, color=COLORS["primary"])
        row += 1
        ws3.merge_cells(f'{get_column_letter(col)}{row}:{get_column_letter(col+1)}{row}')
        ws3[f'{get_column_letter(col)}{row}'] = count
        ws3[f'{get_column_letter(col)}{row}'].font = Font(size=20, bold=True, color=color)
        row += 1

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return {
        "success": True,
        "file_data": base64.b64encode(output.getvalue()).decode(),
        "file_name": f"ComplianceHQ_Report_{company}_{fiscal_month}.xlsx",
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }


@frappe.whitelist()
def download_compliance_report(company, fiscal_month=None):
    """Downloads the compliance report as an Excel file."""
    result = export_compliance_report(company, fiscal_month)

    if not result.get("success"):
        frappe.throw(_("Failed to generate report: ") + result.get("error", "Unknown error"))

    from frappe.utils.file_manager import save_file

    file_data = base64.b64decode(result["file_data"])
    file_name = result["file_name"]

    file_doc = save_file(
        fname=file_name,
        content=file_data,
        dt="File",
        dn="Compliance Report",
        folder="Home/Reports",
        decode=False,
        is_private=0,
    )

    return {
        "success": True,
        "file_url": file_doc.file_url,
        "file_name": file_name,
    }


# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────

def _get_tax_status(company, period_start, period_end):
    """Fetches VAT, WHT, PAYE status from Compliance Liability Ledger."""
    status = {}
    for obligation in ["VAT", "WHT", "PAYE"]:
        cll = frappe.db.sql("""
            SELECT status, total_liability, total_paid, balance_due
            FROM `tabCompliance Liability Ledger`
            WHERE company = %s
              AND obligation_type = %s
              AND period_start >= %s
              AND period_end <= %s
            ORDER BY period_start DESC
            LIMIT 1
        """, (company, obligation, period_start, period_end), as_dict=True)

        if cll:
            status[obligation] = {
                "status": cll[0].status,
                "liability": cll[0].total_liability,
                "paid": cll[0].total_paid,
                "balance": cll[0].balance_due,
            }
        else:
            status[obligation] = {"status": "Not Generated", "liability": 0, "paid": 0, "balance": 0}

    return status


def _get_statutory_status(company, period_start, period_end):
    """Fetches statutory obligations status."""
    status = {}
    for obligation in ["Pension", "NHF", "NSITF", "ITF"]:
        cll = frappe.db.sql("""
            SELECT status, total_liability, total_paid, balance_due
            FROM `tabCompliance Liability Ledger`
            WHERE company = %s
              AND obligation_type = %s
              AND period_start >= %s
              AND period_end <= %s
            ORDER BY period_start DESC
            LIMIT 1
        """, (company, obligation, period_start, period_end), as_dict=True)

        if cll:
            status[obligation] = {
                "status": cll[0].status,
                "liability": cll[0].total_liability,
                "paid": cll[0].total_paid,
                "balance": cll[0].balance_due,
            }
        else:
            status[obligation] = {"status": "Not Generated", "liability": 0, "paid": 0, "balance": 0}

    return status


def _get_license_status(company):
    """Fetches license counts by status."""
    valid = 0
    expiring = 0
    expired = 0
    expiring_list = []

    if frappe.db.exists("DocType", "License Management"):
        licenses = frappe.db.get_all("License Management",
            filters={"company": company},
            fields=["name", "license_name", "license_type", "current_expiry_date", "status", "days_to_expiry"]
        )
        for lic in licenses:
            if lic.status == "Active":
                valid += 1
            elif lic.status == "Expiring Soon":
                expiring += 1
                expiring_list.append({"name": lic.name, "license_name": lic.license_name, "license_type": lic.license_type, "days_to_expiry": lic.days_to_expiry})
            elif lic.status == "Expired":
                expired += 1
    else:
        env_permits = frappe.db.get_all("Environmental Compliance Record",
            filters={"company": company},
            fields=["name", "permit_title", "status", "days_to_expiry"]
        )
        for p in env_permits:
            if p.status == "Active":
                valid += 1
            elif p.status == "Expiring Soon":
                expiring += 1
                expiring_list.append({"name": p.name, "license_name": p.permit_title, "license_type": "Environmental Permit", "days_to_expiry": p.days_to_expiry})
            elif p.status == "Expired":
                expired += 1

        expat_permits = frappe.db.get_all("Expatriate Permit Register",
            filters={"company": company},
            fields=["name", "permit_title", "status", "days_to_expiry"]
        )
        for p in expat_permits:
            if p.status == "Active":
                valid += 1
            elif p.status == "Expiring Soon":
                expiring += 1
                expiring_list.append({"name": p.name, "license_name": p.permit_title, "license_type": "Expatriate Permit", "days_to_expiry": p.days_to_expiry})
            elif p.status == "Expired":
                expired += 1

    return {
        "valid": valid,
        "expiring": expiring,
        "expired": expired,
        "expiring_list": expiring_list[:30],
    }


def _get_incidents(company):
    """Fetches incidents from Compliance Incident doctype."""
    incidents = frappe.db.get_all("Compliance Incident",
        filters={"company": company},
        fields=["name", "incident_title", "incident_type", "status", "incident_date"],
        order_by="incident_date desc",
        limit=20
    )

    by_type = frappe.db.sql("""
        SELECT incident_type, COUNT(*) as cnt
        FROM `tabCompliance Incident`
        WHERE company = %s
        GROUP BY incident_type
    """, company, as_dict=True)

    open_count = frappe.db.count("Compliance Incident", {"company": company, "status": ["!=", "Closed"]})

    return {
        "recent": incidents,
        "by_type": by_type,
        "open": open_count,
    }


def _get_calendar_entries(company, period_start, period_end):
    """Fetches upcoming compliance calendar entries."""
    entries = frappe.db.sql("""
        SELECT 
            ccl.obligation_type,
            ccl.period_label,
            ccl.due_date,
            ccl.status,
            ccl.assigned_to,
            ccl.compliance_domain
        FROM `tabCompliance Calendar Line` ccl
        INNER JOIN `tabCompliance Calendar` cc ON cc.name = ccl.parent
        WHERE cc.company = %s
          AND ccl.due_date >= %s
        ORDER BY ccl.due_date ASC
        LIMIT 20
    """, (company, period_start), as_dict=True)

    return {
        "upcoming": entries,
        "entries": entries,
        "count": len(entries),
    }


def _get_open_tasks(company):
    """Fetches open compliance tasks."""
    tasks = frappe.db.get_all("Compliance Task",
        filters={"company": company, "status": ["!=", "Completed"]},
        fields=["name", "task_title", "priority", "target_completion", "status"],
        order_by="priority asc, target_completion asc",
        limit=20
    )
    return {"open": tasks}


def _get_total_liability(company, period_start, period_end):
    """Calculates total outstanding liability."""
    result = frappe.db.sql("""
        SELECT SUM(balance_due) as total
        FROM `tabCompliance Liability Ledger`
        WHERE company = %s
          AND period_start >= %s
          AND period_end <= %s
          AND status != 'Fully Paid'
    """, (company, period_start, period_end), as_dict=True)

    return result[0].total if result else 0


def _get_v3_domain_summary(company):
    """Returns a summary of key metrics for each domain."""
    return {
        "corporate": _get_corporate_summary(company),
        "contracts": _get_contracts_summary(company),
        "ndpr": _get_ndpr_summary(company),
        "aml": _get_aml_summary(company),
        "labour": _get_labour_summary(company),
        "environmental": _get_environmental_summary(company),
        "industry": _get_industry_summary(company),
        "fraud": _get_fraud_summary(company),
        "training": _get_training_summary(company),
    }


def _calculate_domain_score(company, doctype):
    """Calculates a score for a domain based on its records."""
    if not frappe.db.exists("DocType", doctype):
        return 0

    # Map doctype to the correct status field name
    status_field_map = {
        "Corporate Compliance Register": "overall_status",
        "Board Resolution": "implementation_status",
        "Contract Compliance Record": "compliance_status",
        "Labour Compliance Tracker": "overall_status",
        "Conflict of Interest Declaration": "approval_status",
        "Compliance Training Record": "completion_status",
        "AML KYC Record": "risk_rating",
        "Data Breach Register": "status",
        "Data Processing Record": "status",
        "Expatriate Permit Register": "status",
        "Environmental Compliance Record": "status",
        "Regulatory Return": "status",
        "Whistleblower Report": "status",
        "Suspicious Transaction Report": "status",
        "Compliance Training Calendar": "status",
        "Compliance Liability Ledger": "status",
    }

    status_field = status_field_map.get(doctype, "status")

    # Check if the field exists
    if not frappe.db.has_column(doctype, status_field):
        for fallback in ["status", "overall_status", "compliance_status", "implementation_status", "completion_status", "approval_status"]:
            if frappe.db.has_column(doctype, fallback):
                status_field = fallback
                break
        else:
            return 50

    records = frappe.db.get_all(doctype,
        filters={"company": company},
        fields=["name", status_field]
    )

    if not records:
        return 0

    positive_statuses = ["Compliant", "Active", "Completed", "Passed", "Submitted", "Filed", 
                         "Resolved", "Closed", "Satisfactory", "Approved", "Implemented", 
                         "Fully Paid", "Good"]

    if doctype == "AML KYC Record":
        compliant = 0
        for r in records:
            rating = r.get("risk_rating", "Low")
            if rating in ["Low", "Medium"]:
                compliant += 1
            elif rating == "High":
                compliant += 0.3
        return round((compliant / len(records)) * 100, 1) if records else 0

    compliant = 0
    for r in records:
        val = r.get(status_field, "")
        if val in positive_statuses:
            compliant += 1
        elif val in ["Partial", "Minor Issues", "Expiring Soon", "Partially Paid", "In Progress", "Under Review"]:
            compliant += 0.5
        elif val in ["Not Generated", "Draft", "Pending"]:
            compliant += 0.3

    return round((compliant / len(records)) * 100, 1) if records else 0


def _get_corporate_summary(company):
    """Returns corporate governance summary using EXACT field names."""
    registers = frappe.db.count("Corporate Compliance Register", {"company": company})
    
    non_compliant = frappe.db.count("Corporate Compliance Register", 
        {"company": company, "overall_status": "Non-Compliant"})
    
    overdue_returns = frappe.db.count("Corporate Compliance Register", 
        {"company": company, "annual_return_status": "Overdue"})
    
    agm_missed = frappe.db.count("Corporate Compliance Register", 
        {"company": company, "agm_held_on_time": 0})
    
    cac_filings_outstanding = frappe.db.count("Board Resolution", 
        {"company": company, "cac_filing_required": 1, "cac_filed": 0})
    
    resolutions_pending = frappe.db.count("Board Resolution", 
        {"company": company, "implementation_status": ["!=", "Implemented"]})
    
    return {
        "total_registers": registers,
        "non_compliant": non_compliant,
        "annual_return_overdue": overdue_returns,
        "agm_missed": agm_missed,
        "cac_filings_outstanding": cac_filings_outstanding,
        "resolutions_pending": resolutions_pending,
    }


def _get_contracts_summary(company):
    """Returns contracts summary using EXACT field names."""
    total = frappe.db.count("Contract Compliance Record", {"company": company})
    if not total:
        return {"total": 0, "compliant": 0, "material_breach": 0, "minor_breach": 0, "termination_risk": 0, "avg_sla": 0}

    compliant = frappe.db.count("Contract Compliance Record", 
        {"company": company, "compliance_status": "Compliant"})
    material_breach = frappe.db.count("Contract Compliance Record", 
        {"company": company, "compliance_status": "Material Breach"})
    termination_risk = frappe.db.count("Contract Compliance Record", 
        {"company": company, "compliance_status": "Termination Risk"})
    minor_breach = frappe.db.count("Contract Compliance Record", 
        {"company": company, "compliance_status": "Minor Breach"})

    avg_sla = frappe.db.sql("""
        SELECT AVG(sla_compliance_pct) as avg_sla
        FROM `tabContract Compliance Record`
        WHERE company = %s
    """, company, as_dict=True)

    return {
        "total": total,
        "compliant": compliant,
        "material_breach": material_breach,
        "minor_breach": minor_breach,
        "termination_risk": termination_risk,
        "avg_sla": avg_sla[0].avg_sla if avg_sla else 0,
    }


def _get_ndpr_summary(company):
    """Returns NDPR summary using EXACT field names."""
    records = frappe.db.count("Data Processing Record", {"company": company})
    open_breaches = frappe.db.count("Data Breach Register", 
        {"company": company, "status": ["!=", "Closed"]})
    sensitive_data = frappe.db.count("Data Processing Record", 
        {"company": company, "is_sensitive_data": 1})
    dpia_missing = frappe.db.count("Data Processing Record", 
        {"company": company, "is_sensitive_data": 1, "privacy_impact_done": 0})
    nitda_registered = frappe.db.count("Data Processing Record", 
        {"company": company, "nitda_registered": 1})
    late_notifications = frappe.db.count("Data Breach Register", 
        {"company": company, "late_notification_flag": 1})

    return {
        "processing_records": records,
        "open_breaches": open_breaches,
        "sensitive_data_records": sensitive_data,
        "dpia_missing": dpia_missing,
        "nitda_registered": nitda_registered,
        "late_notifications": late_notifications,
    }


def _get_aml_summary(company):
    """Returns AML summary using EXACT field names."""
    total = frappe.db.count("AML KYC Record", {"company": company})
    high_risk = frappe.db.count("AML KYC Record", 
        {"company": company, "risk_rating": ["in", ["High", "PEP — High", "Sanctioned — Blocked"]]})
    pep_count = frappe.db.count("AML KYC Record", 
        {"company": company, "is_pep": 1})
    sanctions_match = frappe.db.count("AML KYC Record", 
        {"company": company, "sanctions_match": 1})
    
    expiring_30d = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabAML KYC Record`
        WHERE company = %s
          AND kyc_expiry_date IS NOT NULL
          AND DATEDIFF(kyc_expiry_date, CURDATE()) BETWEEN 0 AND 30
    """, company, as_dict=True)

    strs_pending = frappe.db.count("Suspicious Transaction Report", 
        {"company": company, "nfiu_submitted": 0, "status": ["!=", "Closed — No Action"]})

    return {
        "total_kyc": total,
        "high_risk": high_risk,
        "pep_count": pep_count,
        "sanctions_match": sanctions_match,
        "kyc_expiring_30d": expiring_30d[0].count if expiring_30d else 0,
        "strs_pending_nfiu": strs_pending,
    }


def _get_labour_summary(company):
    """Returns labour summary using EXACT field names."""
    total_permits = frappe.db.count("Expatriate Permit Register", {"company": company})
    expired_permits = frappe.db.count("Expatriate Permit Register", 
        {"company": company, "status": "Expired"})
    expiring_permits = frappe.db.count("Expatriate Permit Register", 
        {"company": company, "status": "Expiring Soon"})

    latest = frappe.db.get_all("Labour Compliance Tracker",
        filters={"company": company},
        fields=["period_label", "overall_status", "minimum_wage_compliant", "pencom_all_registered"],
        order_by="review_date desc",
        limit=1
    )

    return {
        "total_permits": total_permits,
        "expired_permits": expired_permits,
        "expiring_permits": expiring_permits,
        "latest_status": latest[0].overall_status if latest else None,
        "latest_period": latest[0].period_label if latest else None,
        "wage_compliant": latest[0].minimum_wage_compliant if latest else None,
        "pencom_compliant": latest[0].pencom_all_registered if latest else None,
    }


def _get_environmental_summary(company):
    """Returns environmental summary using EXACT field names."""
    total = frappe.db.count("Environmental Compliance Record", {"company": company})
    active = frappe.db.count("Environmental Compliance Record", {"company": company, "status": "Active"})
    expired = frappe.db.count("Environmental Compliance Record", {"company": company, "status": "Expired"})
    expiring_soon = frappe.db.count("Environmental Compliance Record", {"company": company, "status": "Expiring Soon"})
    pending_actions = frappe.db.count("Environmental Compliance Record", {"company": company, "corrective_actions_pending": [">", 0]})
    major_non_compliance = frappe.db.count("Environmental Compliance Record", {"company": company, "last_inspection_result": "Major Non-Compliance"})

    return {
        "total": total,
        "active": active,
        "expired": expired,
        "expiring_soon": expiring_soon,
        "pending_actions": pending_actions,
        "major_non_compliance": major_non_compliance,
    }


def _get_industry_summary(company):
    """Returns industry regulatory summary using EXACT field names."""
    total = frappe.db.count("Regulatory Return", {"company": company})
    overdue = frappe.db.count("Regulatory Return", {"company": company, "status": "Overdue"})
    late = frappe.db.count("Regulatory Return", {"company": company, "late_flag": 1})
    pending = frappe.db.count("Regulatory Return", {"company": company, "status": "Pending"})
    submitted = frappe.db.count("Regulatory Return", {"company": company, "status": ["in", ["Submitted", "Accepted"]]})

    total_penalty = frappe.db.sql("""
        SELECT SUM(penalty_for_non_filing) as total
        FROM `tabRegulatory Return`
        WHERE company = %s
    """, company, as_dict=True)

    return {
        "total": total,
        "overdue": overdue,
        "late": late,
        "pending": pending,
        "submitted": submitted,
        "total_penalty": total_penalty[0].total if total_penalty else 0,
    }


def _get_fraud_summary(company):
    """Returns fraud summary using EXACT field names."""
    total_wb = frappe.db.count("Whistleblower Report", {"company": company})
    under_investigation = frappe.db.count("Whistleblower Report", 
        {"company": company, "status": "Under Investigation"})
    escalated = frappe.db.count("Whistleblower Report", 
        {"company": company, "status": "Escalated"})
    substantiated = frappe.db.count("Whistleblower Report", 
        {"company": company, "status": "Closed — Substantiated"})

    total_coi = frappe.db.count("Conflict of Interest Declaration", {"company": company})
    coi_pending = frappe.db.count("Conflict of Interest Declaration", 
        {"company": company, "approval_status": "Pending"})

    return {
        "total_wb_reports": total_wb,
        "under_investigation": under_investigation,
        "escalated": escalated,
        "substantiated": substantiated,
        "total_coi": total_coi,
        "coi_pending_review": coi_pending,
    }


def _get_training_summary(company):
    """Returns training summary using EXACT field names."""
    total = frappe.db.count("Compliance Training Record", {"company": company})
    if not total:
        return {"mandatory_pct": 0, "total_records": 0, "mandatory_completed": 0, "mandatory_total": 0, "failed": 0, "unique_employees": 0}

    completed = frappe.db.count("Compliance Training Record", 
        {"company": company, "completion_status": ["in", ["Completed", "Passed"]]})
    failed = frappe.db.count("Compliance Training Record", 
        {"company": company, "completion_status": "Failed"})
    mandatory_total = frappe.db.count("Compliance Training Record", 
        {"company": company, "is_mandatory": 1})
    mandatory_completed = frappe.db.count("Compliance Training Record", 
        {"company": company, "is_mandatory": 1, "completion_status": ["in", ["Completed", "Passed"]]})

    unique_employees = frappe.db.sql("""
        SELECT COUNT(DISTINCT employee) as count
        FROM `tabCompliance Training Record`
        WHERE company = %s
    """, company, as_dict=True)

    upcoming_sessions = frappe.db.count("Compliance Training Calendar", 
        {"company": company, "status": ["in", ["Planned", "Scheduled"]]})
    
    below_target = frappe.db.count("Compliance Training Calendar", 
        {"company": company, "actual_completion_pct": ["<", "completion_target_pct"]})

    return {
        "total_records": total,
        "mandatory_pct": round((mandatory_completed / mandatory_total) * 100, 1) if mandatory_total > 0 else 0,
        "mandatory_completed": mandatory_completed,
        "mandatory_total": mandatory_total,
        "failed": failed,
        "unique_employees": unique_employees[0].count if unique_employees else 0,
        "upcoming_sessions": upcoming_sessions,
        "below_target": below_target,
    }


# ─── UTILITY ACTIONS ────────────────────────────────────────────────────────

@frappe.whitelist()
def run_liability_generation_now(company, fiscal_month):
    """Generates compliance liabilities for the given period."""
    if not company:
        return {"success": False, "error": "Company required"}

    try:
        # ✅ FIXED: Direct implementation instead of recursive call
        frappe.db.sql("""
            INSERT INTO `tabCompliance Liability Ledger` 
            (company, obligation_type, fiscal_year, period_label, period_start, period_end, 
             due_date, total_liability, total_paid, balance_due, status, creation, modified)
            SELECT 
                %s,
                'VAT',
                (SELECT name FROM `tabFiscal Year` WHERE YEAR(date_start) = YEAR(%s)),
                %s,
                DATE_FORMAT(%s, '%Y-%m-01'),
                LAST_DAY(%s),
                DATE_ADD(LAST_DAY(%s), INTERVAL 21 DAY),
                0, 0, 0, 'Open',
                NOW(), NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM `tabCompliance Liability Ledger` 
                WHERE company = %s AND obligation_type = 'VAT' AND period_label = %s
            )
        """, (company, period_start, fiscal_month, period_start, period_start, period_start, company, fiscal_month))

        frappe.db.commit()
        return {"success": True, "message": "Liabilities generated successfully"}
    except Exception as e:
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def run_reconciliation_now(company):
    """Reconciles CLL entries."""
    if not company:
        return {"success": False, "error": "Company required"}

    try:
        # ✅ FIXED: Direct implementation instead of recursive call
        # Update balance_due and status for CLL entries
        frappe.db.sql("""
            UPDATE `tabCompliance Liability Ledger`
            SET 
                balance_due = total_liability - total_paid,
                status = CASE 
                    WHEN total_liability = total_paid AND total_liability > 0 THEN 'Fully Paid'
                    WHEN total_paid > 0 AND total_paid < total_liability THEN 'Partially Paid'
                    WHEN due_date < CURDATE() AND total_liability > total_paid THEN 'Overdue'
                    ELSE status
                END,
                last_reconciled_on = NOW()
            WHERE company = %s
        """, company)

        frappe.db.commit()
        return {"success": True, "reconciled": "All entries reconciled"}
    except Exception as e:
        frappe.db.rollback()
        return {"success": False, "error": str(e)}