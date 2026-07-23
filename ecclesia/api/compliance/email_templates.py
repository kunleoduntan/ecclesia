# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/compliance_setup/email_templates.py
"""
Compliance Module — HTML Email Templates
All beautiful, branded HTML emails for the compliance system.
Import these in controllers:
    from ecclesia.api.compliance.email_templates import (
        render_breach_alert, render_kyc_approval, etc.
    )
"""

# ── Base layout ────────────────────────────────────────────────────────────────
def _base(content, title, accent="#1E3A5F", badge_text=None, badge_color="#DC2626"):
    badge = ""
    if badge_text:
        badge = f"""
        <div style="text-align:center;margin-bottom:24px">
          <span style="background:{badge_color};color:#fff;font-size:13px;font-weight:700;
                       padding:6px 18px;border-radius:30px;letter-spacing:.5px">{badge_text}</span>
        </div>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#F0F4F8;font-family:'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F0F4F8;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;
       border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.10)">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,{accent} 0%,{accent}dd 60%,#2563EB 100%);
               padding:32px 40px;text-align:center">
      <div style="font-size:28px;margin-bottom:6px">⚖️</div>
      <div style="color:#fff;font-size:20px;font-weight:800;letter-spacing:-.3px">Ecclesia ComplianceHQ</div>
      <div style="color:rgba(255,255,255,.75);font-size:12px;margin-top:4px">Value Impacts Consulting · Powered by Frappe/ERPNext</div>
    </td>
  </tr>

  <!-- CONTENT -->
  <tr>
    <td style="padding:36px 40px">
      {badge}
      <h2 style="margin:0 0 20px;font-size:20px;color:#0F172A;font-weight:700">{title}</h2>
      {content}
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#F8FAFC;padding:20px 40px;border-top:1px solid #E2E8F0;text-align:center">
      <p style="margin:0;font-size:11px;color:#94A3B8">
        This is an automated compliance notification from <strong>Ecclesia ComplianceHQ</strong>.<br>
        Do not reply to this email. Contact your Compliance Officer for queries.<br>
        © 2026 Value Impacts Consulting · Lagos, Nigeria
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body></html>"""


def _kv_row(label, value, value_color="#0F172A"):
    return f"""<tr>
      <td style="padding:8px 0;border-bottom:1px solid #F1F5F9;width:45%;
                 font-size:12px;color:#64748B;font-weight:600">{label}</td>
      <td style="padding:8px 0;border-bottom:1px solid #F1F5F9;
                 font-size:13px;color:{value_color};font-weight:600">{value}</td>
    </tr>"""


def _action_button(label, url, color="#1E3A5F"):
    return f"""<div style="text-align:center;margin:28px 0 8px">
      <a href="{url}" style="background:{color};color:#fff;font-size:14px;font-weight:700;
         padding:13px 32px;border-radius:30px;text-decoration:none;display:inline-block;
         letter-spacing:.3px;box-shadow:0 4px 12px rgba(0,0,0,.2)">{label}</a>
    </div>"""


def _alert_box(text, color="#FEF3C7", border="#D97706", text_color="#92400E"):
    return f"""<div style="background:{color};border-left:4px solid {border};
       border-radius:8px;padding:14px 16px;margin:16px 0;
       font-size:13px;color:{text_color};line-height:1.5">{text}</div>"""


def _stat_row(*stats):
    """stats = list of (label, value, color) tuples"""
    cells = ""
    for lbl, val, col in stats:
        cells += f"""<td style="width:{100//len(stats)}%;text-align:center;
                        padding:16px 8px;background:#F8FAFC;border-radius:10px">
          <div style="font-size:22px;font-weight:800;color:{col}">{val}</div>
          <div style="font-size:11px;color:#94A3B8;margin-top:3px;font-weight:600">{lbl}</div>
        </td>
        <td style="width:8px"></td>"""
    return f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px"><tr>{cells}</tr></table>'


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 1: DATA BREACH ALERT
# ══════════════════════════════════════════════════════════════════════════════
def render_breach_alert(doc):
    """Immediate notification when a Data Breach is reported."""
    severity_colors = {
        "Low": ("#D1FAE5","#059669"),
        "Medium": ("#FEF3C7","#D97706"),
        "High": ("#FEE2E2","#DC2626"),
        "Critical": ("#7F1D1D","#FEE2E2"),
    }
    bg, fg = severity_colors.get(doc.severity, ("#FEE2E2","#DC2626"))

    nitda_warning = ""
    if doc.nitda_notification_required and not doc.nitda_notified:
        nitda_warning = _alert_box(
            "⏰ <strong>NITDA 72-Hour Rule:</strong> This breach requires notification to NITDA within "
            "72 hours of discovery. Please file immediately to avoid regulatory sanctions under the NDPR.",
            "#FEF3C7", "#D97706", "#92400E"
        )

    content = f"""
    {_stat_row(
        ("Severity", doc.severity, fg),
        ("Subjects Affected", str(doc.data_subjects_affected or "Unknown"), "#DC2626"),
        ("Status", doc.status, "#0284C7"),
    )}
    {nitda_warning}
    <p style="font-size:14px;color:#334155;line-height:1.6;margin:0 0 16px">
      A data breach has been reported and requires your immediate attention.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Breach Reference", doc.name)}
      {_kv_row("Company", doc.company)}
      {_kv_row("Breach Date", str(doc.breach_date))}
      {_kv_row("Breach Type", doc.breach_type)}
      {_kv_row("Data Categories", doc.data_categories_breached or "—")}
      {_kv_row("Likely Consequences", doc.likely_consequences or "—")}
      {_kv_row("DPO Sign-off", doc.dpo_sign_off or "Pending", "#D97706")}
    </table>
    {_alert_box(
        "🔒 This notification is confidential. Handle all breach information in accordance with the NDPR and your organisation's data protection policy.",
        "#F0F9FF","#0284C7","#1E40AF"
    )}
    {_action_button("🔍 View Data Breach Register", f"/Form/Data Breach Register/{doc.name}", "#DC2626")}
    """
    return _base(content, f"🚨 Data Breach Alert: {doc.breach_title}",
                 accent="#991B1B", badge_text=f"SEVERITY: {doc.severity.upper()}", badge_color=fg)


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 2: AML / KYC RISK ALERT
# ══════════════════════════════════════════════════════════════════════════════
def render_aml_risk_alert(doc):
    """Alert when AML KYC Record has high/PEP/sanctioned rating."""
    risk_colors = {
        "Low": "#059669", "Medium": "#D97706",
        "High": "#DC2626", "PEP — High": "#7C3AED", "Sanctioned — Blocked": "#7F1D1D"
    }
    risk_color = risk_colors.get(doc.risk_rating, "#DC2626")

    sanctions_box = ""
    if doc.sanctions_match:
        sanctions_box = _alert_box(
            "⛔ <strong>SANCTIONS MATCH DETECTED.</strong> This party has been flagged in sanctions screening. "
            "DO NOT proceed with any transaction. Refer immediately to the AMLCO and legal counsel.",
            "#FEE2E2","#DC2626","#991B1B"
        )
    pep_box = ""
    if doc.is_pep:
        pep_box = _alert_box(
            "🏛️ <strong>PEP (Politically Exposed Person) IDENTIFIED.</strong> Enhanced Due Diligence (EDD) "
            "is mandatory under the Money Laundering (Prevention and Prohibition) Act 2022.",
            "#F5F3FF","#7C3AED","#4C1D95"
        )

    checklist = ""
    checks = [
        ("Identity Verified", bool(doc.identity_verified)),
        ("Address Verified", bool(doc.address_verified)),
        ("Beneficial Owner Identified", bool(doc.beneficial_owner_identified)),
        ("PEP Check Done", bool(doc.pep_check_done)),
        ("Sanctions Check Done", bool(doc.sanctions_check_done)),
    ]
    for lbl, done in checks:
        icon = "✅" if done else "❌"
        color = "#059669" if done else "#DC2626"
        checklist += f'<div style="padding:6px 0;font-size:13px;color:{color}">{icon} {lbl}</div>'

    content = f"""
    {_stat_row(
        ("Risk Rating", doc.risk_rating, risk_color),
        ("KYC Level", doc.kyc_level.split("(")[1].replace(")","") if "(" in doc.kyc_level else doc.kyc_level[:3], "#0284C7"),
        ("Party Type", doc.party_type, "#475569"),
    )}
    {sanctions_box}{pep_box}
    <p style="font-size:14px;color:#334155;line-height:1.6;margin:0 0 16px">
      An AML/KYC record has been flagged and requires review by the AMLCO.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Record Reference", doc.name)}
      {_kv_row("Party Name", doc.party_name_display)}
      {_kv_row("Party Type", doc.party_type)}
      {_kv_row("Company", doc.company)}
      {_kv_row("KYC Date", str(doc.kyc_date))}
      {_kv_row("KYC Expiry", str(doc.kyc_expiry_date or "Not Set"), "#D97706")}
    </table>
    <div style="background:#F8FAFC;border-radius:10px;padding:16px;margin-bottom:20px">
      <div style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;
                  letter-spacing:.5px;margin-bottom:10px">KYC Checklist</div>
      {checklist}
    </div>
    {_alert_box(
        "🔐 Confidential AML Communication — unauthorised disclosure is prohibited under the Money Laundering (Prevention and Prohibition) Act 2022.",
        "#F0F9FF","#0284C7","#1E40AF"
    )}
    {_action_button("🔍 Review KYC Record", f"/Form/AML KYC Record/{doc.name}", "#7C3AED")}
    """
    return _base(content, f"⚠️ AML/KYC Alert: {doc.party_name_display}",
                 accent="#6D28D9", badge_text=f"RISK: {doc.risk_rating.upper()}", badge_color=risk_color)


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 3: SUSPICIOUS TRANSACTION REPORT SUBMITTED
# ══════════════════════════════════════════════════════════════════════════════
def render_str_notification(doc):
    """Internal notification when STR is submitted."""
    content = f"""
    {_alert_box(
        "🔐 <strong>STRICTLY CONFIDENTIAL — AML COMMUNICATION.</strong> "
        "Tipping off is a criminal offence under the Money Laundering (Prevention and Prohibition) Act 2022. "
        "This report must be handled by the AMLCO and relevant authorised persons only.",
        "#FEE2E2","#DC2626","#991B1B"
    )}
    <p style="font-size:14px;color:#334155;line-height:1.6;margin:0 0 16px">
      A Suspicious Transaction Report has been submitted and requires NFIU notification if not already done.
    </p>
    {_stat_row(
        ("Report Type", doc.report_type[:3], "#DC2626"),
        ("Amount (₦)", f"₦{float(doc.transaction_amount or 0):,.0f}", "#1E3A5F"),
        ("NFIU Submitted", "Yes" if doc.nfiu_submitted else "NO", "#059669" if doc.nfiu_submitted else "#DC2626"),
    )}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("STR Reference", doc.name)}
      {_kv_row("Report Type", doc.report_type)}
      {_kv_row("Company", doc.company)}
      {_kv_row("Transaction Date", str(doc.transaction_date))}
      {_kv_row("Party Name", doc.party_name or "Undisclosed")}
      {_kv_row("Suspicious Indicator", doc.suspicious_indicators or "—")}
      {_kv_row("NFIU Reference", doc.nfiu_reference or "Pending submission", "#D97706")}
    </table>
    {"" if doc.nfiu_submitted else _alert_box("⏰ <strong>Action Required:</strong> This STR must be submitted to the NFIU via the goAML system without undue delay.", "#FEF3C7","#D97706","#92400E")}
    {_action_button("📋 View STR", f"/Form/Suspicious Transaction Report/{doc.name}", "#DC2626")}
    """
    return _base(content, f"🚨 STR Notification: {doc.str_title}",
                 accent="#7F1D1D", badge_text="CONFIDENTIAL AML REPORT", badge_color="#DC2626")


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 4: WHISTLEBLOWER REPORT RECEIVED
# ══════════════════════════════════════════════════════════════════════════════
def render_whistleblower_received(doc):
    """Confidential notification to investigation team."""
    content = f"""
    {_alert_box(
        "🔒 <strong>STRICTLY CONFIDENTIAL — WHISTLEBLOWER REPORT.</strong> "
        "Protect the identity of all whistleblowers. Victimisation or retaliation is prohibited "
        "and may constitute a criminal offence.",
        "#FEE2E2","#DC2626","#991B1B"
    )}
    <p style="font-size:14px;color:#334155;line-height:1.6;margin:0 0 16px">
      A new whistleblower report has been received and assigned for investigation.
    </p>
    {_stat_row(
        ("Report Code", doc.report_code or doc.name[:8], "#7C3AED"),
        ("Severity", doc.severity, "#DC2626" if doc.severity in ("High","Critical") else "#D97706"),
        ("Anonymous", "Yes" if doc.is_anonymous else "No", "#475569"),
    )}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Report Code", doc.report_code or doc.name)}
      {_kv_row("Date Received", str(doc.received_date))}
      {_kv_row("Channel", doc.channel)}
      {_kv_row("Category", doc.report_category)}
      {_kv_row("Company", doc.company)}
      {_kv_row("Alleged Department", doc.alleged_department or "Not Specified")}
      {_kv_row("Estimated Impact", f"₦{float(doc.estimated_financial_impact or 0):,.0f}")}
    </table>
    <div style="background:#F5F3FF;border-radius:10px;padding:16px;margin-bottom:20px">
      <div style="font-size:12px;font-weight:700;color:#6D28D9;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">Investigation Protocol</div>
      <div style="font-size:13px;color:#4C1D95;line-height:1.7">
        ✅ Assign a qualified investigator within 48 hours<br>
        ✅ Maintain strict confidentiality throughout<br>
        ✅ Document all investigation steps<br>
        ✅ Escalate to board / external authority if required<br>
        ✅ Provide feedback to whistleblower (if not anonymous)
      </div>
    </div>
    {_action_button("🔍 Access Report (Authorised Users Only)", f"/Form/Whistleblower Report/{doc.name}", "#7C3AED")}
    """
    return _base(content, "🔒 Whistleblower Report Received",
                 accent="#4C1D95", badge_text="CONFIDENTIAL — INVESTIGATION REQUIRED", badge_color="#7C3AED")


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 5: COI DECLARATION — LINE MANAGER REVIEW
# ══════════════════════════════════════════════════════════════════════════════
def render_coi_review_request(doc):
    """Request to line manager to review and acknowledge a COI declaration."""
    conflict_section = ""
    if doc.has_conflict:
        conflict_section = f"""
        {_alert_box(
            f"⚠️ <strong>Conflict Declared:</strong> {doc.conflict_type or 'See declaration for details'}. "
            f"{'Estimated Value: ₦' + f'{float(doc.financial_value or 0):,.0f}' if doc.financial_interest else ''} "
            f"{'Recusal required.' if doc.recusal_required else ''}",
            "#FEF3C7","#D97706","#92400E"
        )}"""
    else:
        conflict_section = _alert_box(
            "✅ <strong>No Conflict Declared.</strong> The employee has confirmed they have no conflict of interest to disclose at this time.",
            "#D1FAE5","#059669","#065F46"
        )

    content = f"""
    <p style="font-size:14px;color:#334155;line-height:1.6;margin:0 0 16px">
      An employee has submitted a Conflict of Interest Declaration that requires your review and acknowledgement.
    </p>
    {_stat_row(
        ("Declaration Type", doc.declaration_type.split()[0], "#0284C7"),
        ("Has Conflict", "YES" if doc.has_conflict else "None", "#DC2626" if doc.has_conflict else "#059669"),
        ("Status", doc.approval_status, "#D97706"),
    )}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Declaration Ref", doc.name)}
      {_kv_row("Employee", doc.employee)}
      {_kv_row("Department", doc.department or "—")}
      {_kv_row("Designation", doc.designation or "—")}
      {_kv_row("Declaration Date", str(doc.declaration_date))}
      {_kv_row("Fiscal Year", doc.fiscal_year or "—")}
    </table>
    {conflict_section}
    <div style="background:#F8FAFC;border-radius:10px;padding:16px;margin-bottom:20px">
      <div style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">Your Action Required</div>
      <div style="font-size:13px;color:#334155;line-height:1.7">
        Please review this declaration and:<br>
        1. Acknowledge receipt (tick "Line Manager Acknowledged" on the form)<br>
        2. {'Assess proposed mitigation and recusal arrangement' if doc.has_conflict else 'File for record — no further action needed'}<br>
        3. Escalate to HR/Board if the conflict is material
      </div>
    </div>
    {_action_button("✍️ Review & Acknowledge Declaration", f"/Form/Conflict of Interest Declaration/{doc.name}", "#1E3A5F")}
    """
    return _base(content, f"Conflict of Interest Declaration: {doc.employee}",
                 accent="#1E3A5F", badge_text=f"{'⚠️ CONFLICT DECLARED' if doc.has_conflict else '✅ NO CONFLICT DECLARED'}",
                 badge_color="#DC2626" if doc.has_conflict else "#059669")


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 6: PERMIT / LICENCE EXPIRY ALERT
# ══════════════════════════════════════════════════════════════════════════════
def render_permit_expiry_alert(doc_name, doc_type, permit_name, company,
                                expiry_date, days_to_expiry, responsible_officer,
                                renewal_cost=None, renewal_lead_days=90):
    days_color = "#DC2626" if days_to_expiry <= 30 else "#D97706" if days_to_expiry <= 90 else "#059669"
    urgency = "CRITICAL" if days_to_expiry <= 7 else "URGENT" if days_to_expiry <= 30 else "ATTENTION REQUIRED"
    badge_color = "#DC2626" if days_to_expiry <= 30 else "#D97706"

    cost_row = _kv_row("Estimated Renewal Cost", f"₦{float(renewal_cost or 0):,.0f}") if renewal_cost else ""

    content = f"""
    {_stat_row(
        ("Days to Expiry", str(days_to_expiry), days_color),
        ("Expiry Date", str(expiry_date), days_color),
        ("Renewal Lead Time", f"{renewal_lead_days}d", "#475569"),
    )}
    <p style="font-size:14px;color:#334155;line-height:1.6;margin:0 0 16px">
      A permit or licence is approaching expiry and requires immediate renewal action.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Permit / Licence", permit_name)}
      {_kv_row("Document Type", doc_type)}
      {_kv_row("Company", company)}
      {_kv_row("Expiry Date", str(expiry_date), days_color)}
      {_kv_row("Days Remaining", str(days_to_expiry), days_color)}
      {_kv_row("Responsible Officer", responsible_officer or "Not Assigned", "#D97706")}
      {cost_row}
    </table>
    {_alert_box(
        f"⚡ <strong>Renewal Action:</strong> Allow at least {renewal_lead_days} days for processing. "
        f"Operating with an expired permit is a regulatory offence and may result in fines, shutdown, or prosecution.",
        "#FEF3C7" if days_to_expiry > 7 else "#FEE2E2",
        "#D97706" if days_to_expiry > 7 else "#DC2626",
        "#92400E" if days_to_expiry > 7 else "#991B1B"
    )}
    {_action_button("🔄 Initiate Renewal", f"/Form/{doc_type}/{doc_name}", "#1E3A5F")}
    """
    return _base(content, f"⚠️ {urgency}: {permit_name}",
                 accent="#92400E" if days_to_expiry <= 30 else "#1E3A5F",
                 badge_text=f"⏰ {days_to_expiry} DAYS TO EXPIRY", badge_color=badge_color)


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 7: REGULATORY RETURN OVERDUE
# ══════════════════════════════════════════════════════════════════════════════
def render_regulatory_return_overdue(doc):
    content = f"""
    {_stat_row(
        ("Status", doc.status, "#DC2626"),
        ("Authority", (doc.authority or "")[:12], "#1E3A5F"),
        ("Penalty Risk", f"₦{float(doc.penalty_for_non_filing or 0):,.0f}", "#DC2626"),
    )}
    {_alert_box(
        f"🚨 <strong>OVERDUE REGULATORY RETURN.</strong> The {doc.return_title} to "
        f"{doc.authority} was due {doc.due_date}. Immediate filing is required to avoid regulatory sanctions.",
        "#FEE2E2","#DC2626","#991B1B"
    )}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Return Reference", doc.name)}
      {_kv_row("Return Type", doc.return_type)}
      {_kv_row("Authority", doc.authority)}
      {_kv_row("Industry", doc.industry_category)}
      {_kv_row("Period", doc.period_covered or "—")}
      {_kv_row("Due Date", str(doc.due_date), "#DC2626")}
      {_kv_row("Penalty for Non-Filing", f"₦{float(doc.penalty_for_non_filing or 0):,.0f}", "#DC2626")}
      {_kv_row("Filed By", doc.filed_by or "Not Assigned", "#D97706")}
    </table>
    {_action_button("📋 File Return Now", f"/Form/Regulatory Return/{doc.name}", "#DC2626")}
    """
    return _base(content, f"🚨 Overdue: {doc.return_title}",
                 accent="#7F1D1D", badge_text="REGULATORY RETURN OVERDUE", badge_color="#DC2626")


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 8: LABOUR COMPLIANCE ISSUES
# ══════════════════════════════════════════════════════════════════════════════
def render_labour_compliance_alert(doc):
    issues = []
    if not doc.minimum_wage_compliant:
        issues.append(("🚫", "Minimum wage non-compliance detected", "DC2626"))
    if not doc.working_hours_compliant:
        issues.append(("⏰", "Working hours exceed statutory limit", "D97706"))
    if not doc.statutory_leave_compliant:
        issues.append(("📅", "Statutory leave entitlements not met", "D97706"))
    if not doc.employment_contracts_compliant:
        issues.append(("📄", "Employment contracts not fully signed", "D97706"))
    if not doc.pencom_all_registered:
        issues.append(("🏦", "Not all employees registered with PenCom", "DC2626"))

    issues_html = ""
    for icon, text, col in issues:
        issues_html += f'<div style="padding:8px 12px;background:#FEF2F2;border-left:3px solid #{col};border-radius:6px;margin-bottom:8px;font-size:13px;color:#1E293B">{icon} {text}</div>'

    content = f"""
    {_stat_row(
        ("Overall Status", doc.overall_status, "#DC2626" if doc.overall_status=="Non-Compliant" else "#D97706"),
        ("Total Employees", str(doc.total_employees or 0), "#1E3A5F"),
        ("Issues Found", str(len(issues)), "#DC2626" if issues else "#059669"),
    )}
    <p style="font-size:14px;color:#334155;line-height:1.6;margin:0 0 16px">
      The Labour Compliance Tracker for <strong>{doc.period_label}</strong> has been reviewed
      with status: <strong>{doc.overall_status}</strong>.
    </p>
    {issues_html if issues_html else _alert_box("✅ No critical labour compliance issues identified for this period.", "#D1FAE5","#059669","#065F46")}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Tracker Reference", doc.name)}
      {_kv_row("Company", doc.company)}
      {_kv_row("Period", doc.period_label)}
      {_kv_row("Review Date", str(doc.review_date))}
      {_kv_row("Minimum Wage (Current)", f"₦{float(doc.current_min_wage or 0):,.0f}")}
      {_kv_row("Lowest Gross Paid", f"₦{float(doc.lowest_gross_paid or 0):,.0f}", "#DC2626" if not doc.minimum_wage_compliant else "#059669")}
    </table>
    {_action_button("📋 View Labour Tracker", f"/Form/Labour Compliance Tracker/{doc.name}", "#1E3A5F")}
    """
    return _base(content, f"Labour Compliance Review: {doc.period_label}",
                 accent="#1E3A5F", badge_text=doc.overall_status.upper(),
                 badge_color="#DC2626" if doc.overall_status == "Non-Compliant" else "#D97706")


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 9: TRAINING COMPLETION CERTIFICATE
# ══════════════════════════════════════════════════════════════════════════════
def render_training_completion(doc):
    passed_color = "#059669" if doc.passed else "#DC2626"
    badge_text = "TRAINING COMPLETED ✅" if doc.passed else "TRAINING FAILED ❌"
    badge_color = "#059669" if doc.passed else "#DC2626"

    cert_section = ""
    if doc.passed and doc.certificate_number:
        cert_section = f"""
        <div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);
                    border-radius:12px;padding:24px;text-align:center;margin-bottom:20px">
          <div style="color:rgba(255,255,255,.7);font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">Certificate of Completion</div>
          <div style="color:#fff;font-size:18px;font-weight:800;margin-bottom:4px">{doc.training_title}</div>
          <div style="color:rgba(255,255,255,.8);font-size:13px">Certificate No: <strong>{doc.certificate_number}</strong></div>
          {'<div style="color:rgba(255,255,255,.7);font-size:11px;margin-top:4px">Valid until: ' + str(doc.certificate_expiry) + '</div>' if doc.certificate_expiry else ''}
        </div>"""

    content = f"""
    {cert_section}
    {_stat_row(
        ("Category", doc.training_category[:6], "#1E3A5F"),
        ("Score", f"{doc.score or 0:.0f}%", passed_color),
        ("Status", doc.completion_status, passed_color),
    )}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Training Title", doc.training_title)}
      {_kv_row("Employee", doc.employee)}
      {_kv_row("Category", doc.training_category)}
      {_kv_row("Training Date", str(doc.training_date))}
      {_kv_row("Provider", doc.training_provider or "—")}
      {_kv_row("Duration", f"{doc.duration_hours or 0:.1f} hours")}
      {_kv_row("Mandatory", "Yes" if doc.is_mandatory else "No")}
      {_kv_row("Result", "PASSED ✅" if doc.passed else "FAILED ❌", passed_color)}
    </table>
    {_alert_box(
        "📚 Please ensure all mandatory compliance training is completed before the deadline. "
        "Non-completion may be escalated to the HR and Compliance teams.",
        "#F0F9FF","#0284C7","#1E40AF"
    ) if not doc.passed else ""}
    {_action_button("📄 View Training Record", f"/Form/Compliance Training Record/{doc.name}", "#1E3A5F")}
    """
    return _base(content, f"Training: {doc.training_title}",
                 accent="#1E3A5F", badge_text=badge_text, badge_color=badge_color)


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 10: BOARD RESOLUTION — IMPLEMENTATION REMINDER
# ══════════════════════════════════════════════════════════════════════════════
def render_board_resolution_reminder(doc):
    cac_section = ""
    if doc.cac_filing_required and not doc.cac_filed:
        cac_section = _alert_box(
            f"📋 <strong>CAC Filing Required.</strong> This resolution requires a CAC form to be filed. "
            f"Filing reference: {doc.cac_filing_reference or 'Not yet filed'}. "
            f"Please file within 15 days of the meeting date.",
            "#FEF3C7","#D97706","#92400E"
        )

    content = f"""
    {_stat_row(
        ("Meeting Type", doc.meeting_type[:5], "#1E3A5F"),
        ("Category", (doc.resolution_category or "")[:8], "#0284C7"),
        ("Status", doc.implementation_status, "#D97706"),
    )}
    {cac_section}
    <p style="font-size:14px;color:#334155;line-height:1.6;margin:0 0 16px">
      This is a reminder to implement the Board Resolution detailed below.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Resolution Reference", doc.name)}
      {_kv_row("Resolution Number", doc.resolution_number or "—")}
      {_kv_row("Meeting Type", doc.meeting_type)}
      {_kv_row("Meeting Date", str(doc.meeting_date))}
      {_kv_row("Category", doc.resolution_category or "—")}
      {_kv_row("Responsible Officer", doc.responsible_officer or "Not Assigned", "#D97706")}
      {_kv_row("Implementation Status", doc.implementation_status, "#D97706")}
    </table>
    <div style="background:#F8FAFC;border-radius:10px;padding:16px;margin-bottom:20px">
      <div style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">Resolution Summary</div>
      <p style="font-size:13px;color:#334155;line-height:1.6;margin:0">{(doc.resolution_text or "See attached resolution document.")[:400]}</p>
    </div>
    {_action_button("📋 Update Implementation Status", f"/Form/Board Resolution/{doc.name}", "#1E3A5F")}
    """
    return _base(content, f"Board Resolution: {doc.resolution_title}",
                 accent="#1E3A5F", badge_text="IMPLEMENTATION REQUIRED", badge_color="#D97706")


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 11: CORPORATE COMPLIANCE — STATUS SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
def render_corporate_compliance_summary(doc):
    status_color = {
        "Compliant": "#059669",
        "Minor Issues": "#D97706",
        "Major Issues": "#DC2626",
        "Non-Compliant": "#7F1D1D"
    }.get(doc.overall_status, "#475569")

    checkmarks = [
        ("CAC Annual Return", doc.annual_return_status in ("Filed On Time","Exempt","Not Due")),
        ("AGM Held On Time", bool(doc.agm_held_on_time)),
        ("Director Changes Notified", bool(doc.director_changes_notified)),
        ("Shareholder Changes Notified", bool(doc.shareholder_changes_notified)),
        ("Registered Address Current", bool(doc.registered_address_current)),
        ("Statutory Registers Updated", bool(doc.statutory_registers_current)),
    ]
    checks_html = "".join([
        f'<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #F1F5F9">'
        f'<span style="font-size:16px">{"✅" if ok else "❌"}</span>'
        f'<span style="font-size:13px;color:{"#059669" if ok else "#DC2626"};font-weight:600">{lbl}</span>'
        f'</div>'
        for lbl, ok in checkmarks
    ])

    content = f"""
    {_stat_row(
        ("Overall Status", doc.overall_status, status_color),
        ("CAC Return", doc.annual_return_status[:8], "#0284C7"),
        ("Fiscal Year", str(doc.fiscal_year or "—"), "#475569"),
    )}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("Register Reference", doc.name)}
      {_kv_row("Company", doc.company)}
      {_kv_row("RC Number", doc.rc_number or "—")}
      {_kv_row("Company Secretary", doc.company_secretary or "—")}
      {_kv_row("Annual Return Due", str(doc.annual_return_due_date))}
      {_kv_row("Annual Return Filed", str(doc.annual_return_filed_date or "NOT FILED"), "#DC2626" if not doc.annual_return_filed_date else "#059669")}
      {_kv_row("Next AGM Due", str(doc.next_agm_due_date or "—"))}
    </table>
    <div style="background:#F8FAFC;border-radius:10px;padding:16px;margin-bottom:20px">
      <div style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">Corporate Compliance Checklist</div>
      {checks_html}
    </div>
    {_action_button("📋 View Corporate Register", f"/Form/Corporate Compliance Register/{doc.name}", "#1E3A5F")}
    """
    return _base(content, f"Corporate Compliance: {doc.company}",
                 accent="#1E3A5F", badge_text=doc.overall_status.upper(), badge_color=status_color)


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE 12: CONTRACT COMPLIANCE BREACH
# ══════════════════════════════════════════════════════════════════════════════
def render_contract_breach_alert(doc):
    status_colors = {
        "Compliant": "#059669",
        "Minor Breach": "#D97706",
        "Material Breach": "#DC2626",
        "Termination Risk": "#7F1D1D",
        "Expired": "#94A3B8"
    }
    status_color = status_colors.get(doc.compliance_status, "#DC2626")

    content = f"""
    {_stat_row(
        ("Status", doc.compliance_status.split()[0], status_color),
        ("SLA Compliance", f"{float(doc.sla_compliance_pct or 0):.0f}%", "#059669" if (doc.sla_compliance_pct or 0) >= 90 else "#DC2626"),
        ("Open Breaches", str(doc.open_breaches or 0), "#DC2626" if (doc.open_breaches or 0) > 0 else "#059669"),
    )}
    {_alert_box(
        f"⚠️ Contract compliance status has changed to <strong>{doc.compliance_status}</strong>. "
        f"{'Immediate legal review recommended.' if doc.compliance_status in ('Material Breach','Termination Risk') else 'Please review and resolve the identified breaches.'}",
        "#FEF3C7","#D97706","#92400E"
    )}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
      {_kv_row("CCR Reference", doc.name)}
      {_kv_row("Contract", doc.compliance_title)}
      {_kv_row("Vendor", doc.vendor or "—")}
      {_kv_row("Contract End", str(doc.contract_end or "—"))}
      {_kv_row("Next Review", str(doc.next_review_date or "—"))}
      {_kv_row("Contract Value", f"₦{float(doc.contract_value or 0):,.0f}")}
      {_kv_row("Unmet Obligations", doc.unmet_obligations or "None", "#DC2626" if doc.unmet_obligations else "#059669")}
    </table>
    {_action_button("📄 Review Contract Compliance", f"/Form/Contract Compliance Record/{doc.name}", "#1E3A5F")}
    """
    return _base(content, f"Contract Alert: {doc.compliance_title}",
                 accent="#1E3A5F" if doc.compliance_status == "Compliant" else "#7F1D1D",
                 badge_text=f"CONTRACT STATUS: {doc.compliance_status.upper()}", badge_color=status_color)


# ── Utility: send an email using a template function ──────────────────────────
def send_compliance_email(recipients, subject, html_body, cc=None):
    """Safe wrapper around frappe.sendmail for compliance emails."""
    import frappe as _frappe
    if not recipients:
        return
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [r for r in recipients if r]
    if not recipients:
        return
    try:
        _frappe.sendmail(
            recipients=recipients,
            cc=cc or [],
            subject=subject,
            message=html_body,
            now=False  # queue — don't block the request
        )
    except Exception as e:
        _frappe.log_error(f"Compliance email failed ({subject}): {e}", "Compliance Email")