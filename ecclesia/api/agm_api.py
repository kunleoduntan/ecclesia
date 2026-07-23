# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/agm_api.py
"""
AGM API — Notifications, Dashboard, and Compliance helpers
=============================================================
Whitelisted methods:
    get_upcoming_agm_obligations(company, days_ahead)
    get_agm_dashboard_stats(company)
    send_agm_notice(agm_name, channel)
    send_agm_reminder(agm_name, reminder_type)
    send_proxy_confirmation(agm_name, proxy_row_name)
    send_minutes_notification(agm_name)
    send_cac_deadline_alert(agm_name)
    send_resolution_implementation_alert(agm_name)
    run_agm_scheduled_notifications()   ← called by scheduler

Notification triggers:
    1. AGM Notice          → All shareholders (21+ days before)
    2. AGM Reminder        → All shareholders (7 days before)
    3. AGM Day Alert       → Chairperson + Company Secretary (on the day)
    4. Proxy Confirmation  → Proxy appointer (on receipt of proxy form)
    5. Minutes Ready       → All attendees (after minutes approved)
    6. CAC Deadline Alert  → Company Secretary + Finance (14 days before, 7 days before, on deadline)
    7. Resolution Alert    → Responsible officers (after AGM, per resolution)
    8. Late AGM Warning    → Board + Secretary (when AGM overdue)
"""

import frappe
from frappe import _
from frappe.utils import (
    getdate, today, date_diff, add_days, nowdate,
    cint, flt, now_datetime, formatdate
)


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD & COMPLIANCE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_upcoming_agm_obligations(company=None, days_ahead=90):
    """
    Return AGM dates and CAC deadlines within the next N days.
    Used by ComplianceHQ dashboard.
    """
    agms = frappe.db.get_all(
        "Annual General Meeting",
        filters={**({"company": company} if company else {}),
                 "status": ["not in", ["Closed", "Cancelled"]]},
        fields=["name", "agm_title", "company", "agm_date", "status",
                "cac_filed", "cac_filing_deadline", "notice_date", "notice_compliant"],
        order_by="agm_date asc",
        limit=50,
    )
    today_date = getdate(today())
    obligations = []

    for agm in agms:
        agm_date     = getdate(agm.agm_date)     if agm.agm_date             else None
        cac_deadline = getdate(agm.cac_filing_deadline) if agm.cac_filing_deadline else None

        if agm_date:
            days_to = date_diff(agm_date, today_date)
            if -30 <= days_to <= int(days_ahead):
                obligations.append({
                    "type":        "AGM",
                    "title":       agm.agm_title,
                    "company":     agm.company,
                    "due_date":    str(agm_date),
                    "days_to":     days_to,
                    "status":      agm.status,
                    "doc_name":    agm.name,
                    "overdue":     days_to < 0,
                    "alert_level": "red"   if days_to < 0
                              else "amber" if days_to <= 21
                              else "green",
                })

        if cac_deadline and not agm.cac_filed:
            days_to_cac = date_diff(cac_deadline, today_date)
            if -30 <= days_to_cac <= int(days_ahead):
                obligations.append({
                    "type":        "CAC Annual Return",
                    "title":       f"CAC Return — {agm.agm_title}",
                    "company":     agm.company,
                    "due_date":    str(cac_deadline),
                    "days_to":     days_to_cac,
                    "status":      "Pending Filing",
                    "doc_name":    agm.name,
                    "overdue":     days_to_cac < 0,
                    "alert_level": "red"   if days_to_cac < 0
                              else "amber" if days_to_cac <= 14
                              else "green",
                })

    return sorted(obligations, key=lambda x: x["days_to"])


@frappe.whitelist()
def get_agm_dashboard_stats(company=None):
    """KPI summary for the corporate governance dashboard."""
    all_agms = frappe.db.get_all(
        "Annual General Meeting",
        filters=({"company": company} if company else {}),
        fields=["name", "agm_date", "status", "cac_filed",
                "cac_filing_deadline", "notice_compliant", "quorum_met"],
    )
    today_date  = getdate(today())
    current_year = today_date.year

    return {
        "total":            len(all_agms),
        "held_this_year":   sum(1 for a in all_agms
                                if a.status in ("Held","Minutes Approved","CAC Filed","Closed")
                                and a.agm_date and getdate(a.agm_date).year == current_year),
        "cac_filed":        sum(1 for a in all_agms if a.cac_filed),
        "cac_overdue":      sum(1 for a in all_agms
                                if not a.cac_filed and a.cac_filing_deadline
                                and getdate(a.cac_filing_deadline) < today_date),
        "notice_compliant": sum(1 for a in all_agms if a.notice_compliant),
        "quorum_met":       sum(1 for a in all_agms if a.quorum_met),
        "upcoming_90_days": sum(1 for a in all_agms
                                if a.agm_date
                                and 0 <= date_diff(getdate(a.agm_date), today_date) <= 90),
        "overdue_agm":      sum(1 for a in all_agms
                                if a.status not in ("Held","Minutes Approved","CAC Filed","Closed","Cancelled")
                                and a.agm_date and getdate(a.agm_date) < today_date),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATION ENTRY POINTS (whitelisted — callable from JS buttons)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def send_agm_notice(agm_name, channel="Email"):
    """
    Send the formal AGM Notice to all shareholders in the Notice Delivery Log.
    Triggered by the 📧 Send AGM Notices button.
    """
    agm = frappe.get_doc("Annual General Meeting", agm_name)

    if not agm.notice_logs:
        frappe.throw(_("No recipients in Notice Delivery Log. "
                       "Add shareholders or use Load Shareholders from Register."))

    today_date = getdate(today())
    agm_date   = getdate(agm.agm_date)
    days_to    = date_diff(agm_date, today_date)
    min_notice = 21 if agm.agm_type == "Annual General Meeting" else 14

    sent = 0; failed = 0

    for row in agm.notice_logs:
        if row.delivery_status in ("Delivered", "Sent"):
            continue
        if not row.email:
            row.delivery_status = "Failed"
            row.remarks = "No email address"
            failed += 1
            continue
        try:
            frappe.sendmail(
                recipients = [row.email],
                subject    = f"Notice of {agm.agm_type} — {agm.company}",
                message    = _build_agm_notice_html(agm, row.shareholder_name, days_to, min_notice),
                reference_doctype = "Annual General Meeting",
                reference_name    = agm_name,
            )
            row.delivery_status = "Sent"
            row.sent_date       = today()
            sent += 1
        except Exception as e:
            row.delivery_status = "Failed"
            row.remarks = str(e)[:200]
            failed += 1

    agm.members_notified = sent
    if sent > 0 and agm.status == "Planning":
        agm.notice_date = today()
        agm.status      = "Notices Sent"
    agm.save(ignore_permissions=True)

    return {
        "sent":    sent,
        "failed":  failed,
        "total":   len(agm.notice_logs),
        "message": f"✅ {sent} notice(s) sent. ❌ {failed} failed.",
    }


@frappe.whitelist()
def send_agm_reminder(agm_name, reminder_type="7_day"):
    """
    Send a reminder to all shareholders who were notified.
    reminder_type: '7_day' | '24_hour' | 'day_of'
    """
    agm    = frappe.get_doc("Annual General Meeting", agm_name)
    labels = {
        "7_day":    ("7-Day Reminder", "7 days"),
        "24_hour":  ("24-Hour Reminder", "tomorrow"),
        "day_of":   ("Meeting Today", "today"),
    }
    label, when = labels.get(reminder_type, ("Reminder", "soon"))

    recipients = [r.email for r in (agm.notice_logs or [])
                  if r.email and r.delivery_status in ("Sent", "Delivered")]
    if not recipients:
        return {"sent": 0, "message": "No previously notified shareholders found."}

    sent = 0
    for email in recipients:
        try:
            frappe.sendmail(
                recipients = [email],
                subject    = f"Reminder — {agm.agm_type} {label} — {agm.company}",
                message    = _build_reminder_html(agm, label, when),
                reference_doctype = "Annual General Meeting",
                reference_name    = agm_name,
            )
            sent += 1
        except Exception:
            pass

    # Also alert chairperson and company secretary on day-of
    if reminder_type == "day_of":
        _notify_internal_officers(agm, "day_of")

    frappe.get_doc({
        "doctype":           "Comment",
        "comment_type":      "Info",
        "reference_doctype": "Annual General Meeting",
        "reference_name":    agm_name,
        "content": f"AGM {label} sent to {sent} shareholder(s) — {now_datetime()}",
    }).insert(ignore_permissions=True)

    return {"sent": sent, "message": f"Reminder sent to {sent} shareholder(s)."}


@frappe.whitelist()
def send_proxy_confirmation(agm_name, proxy_row_name):
    """
    Send a confirmation email to the shareholder who submitted a proxy form.
    Triggered when a proxy row is saved/validated.
    """
    agm   = frappe.get_doc("Annual General Meeting", agm_name)
    proxy = next((p for p in (agm.proxies or []) if p.name == proxy_row_name), None)
    if not proxy:
        frappe.throw(_("Proxy row not found."))

    # Try to get appointer's email from notice log
    email = None
    for row in (agm.notice_logs or []):
        if row.shareholder_name == proxy.appointing_member and row.email:
            email = row.email
            break

    if not email:
        return {"sent": 0, "message": "No email found for appointing shareholder."}

    frappe.sendmail(
        recipients        = [email],
        subject           = f"Proxy Form Received — {agm.company} {agm.agm_type}",
        message           = _build_proxy_confirmation_html(agm, proxy),
        reference_doctype = "Annual General Meeting",
        reference_name    = agm_name,
    )
    return {"sent": 1, "message": f"Proxy confirmation sent to {email}."}


@frappe.whitelist()
def send_minutes_notification(agm_name):
    """
    Notify all attendees that the AGM minutes have been approved.
    Triggered when status changes to 'Minutes Approved'.
    """
    agm = frappe.get_doc("Annual General Meeting", agm_name)

    if agm.status != "Minutes Approved":
        frappe.throw(_("Minutes notification can only be sent when status is 'Minutes Approved'."))

    # Collect all attendee emails from notice log + attendees
    emails = set()
    for row in (agm.notice_logs or []):
        if row.email and row.delivery_status in ("Sent", "Delivered"):
            emails.add(row.email)

    # Also send to chairperson and company secretary
    for officer in [agm.chairperson, agm.company_secretary]:
        if officer:
            emp_email = frappe.db.get_value("Employee", officer,
                                            ["company_email", "personal_email"], as_dict=True)
            if emp_email:
                emails.add(emp_email.company_email or emp_email.personal_email or "")

    emails = {e for e in emails if e}
    if not emails:
        return {"sent": 0, "message": "No recipients found."}

    sent = 0
    for email in emails:
        try:
            frappe.sendmail(
                recipients        = [email],
                subject           = f"AGM Minutes Approved — {agm.company}",
                message           = _build_minutes_notification_html(agm),
                reference_doctype = "Annual General Meeting",
                reference_name    = agm_name,
            )
            sent += 1
        except Exception:
            pass

    return {"sent": sent, "message": f"Minutes notification sent to {sent} recipient(s)."}


@frappe.whitelist()
def send_cac_deadline_alert(agm_name):
    """
    Send CAC filing deadline alert to company secretary and finance.
    Called manually or by scheduler.
    """
    agm = frappe.get_doc("Annual General Meeting", agm_name)
    if agm.cac_filed:
        return {"sent": 0, "message": "CAC already filed — no alert needed."}

    today_date   = getdate(today())
    cac_deadline = getdate(agm.cac_filing_deadline) if agm.cac_filing_deadline else None
    if not cac_deadline:
        return {"sent": 0, "message": "No CAC filing deadline set."}

    days_to = date_diff(cac_deadline, today_date)
    is_overdue = days_to < 0

    emails = set()
    for officer in [agm.company_secretary, agm.chairperson]:
        if officer:
            emp = frappe.db.get_value("Employee", officer,
                                      ["company_email", "personal_email"], as_dict=True)
            if emp:
                emails.add(emp.company_email or emp.personal_email or "")

    # Add Accounts Manager users
    acct_mgr_users = frappe.db.get_all("User",
        filters={"role_profile_name": ["like", "%Accounts%"]},
        fields=["email"], limit=5)
    for u in acct_mgr_users:
        if u.email:
            emails.add(u.email)

    emails = {e for e in emails if e}
    if not emails:
        return {"sent": 0, "message": "No recipients found."}

    sent = 0
    for email in emails:
        try:
            frappe.sendmail(
                recipients        = [email],
                subject           = (
                    f"🚨 OVERDUE: CAC Annual Return — {agm.company}"
                    if is_overdue else
                    f"⚠️ CAC Annual Return Due in {days_to} Days — {agm.company}"
                ),
                message           = _build_cac_alert_html(agm, days_to, is_overdue),
                reference_doctype = "Annual General Meeting",
                reference_name    = agm_name,
            )
            sent += 1
        except Exception:
            pass

    return {"sent": sent, "message": f"CAC alert sent to {sent} recipient(s). Days to deadline: {days_to}."}


@frappe.whitelist()
def send_resolution_implementation_alert(agm_name):
    """
    Send each responsible officer their resolution implementation task(s).
    Called after AGM is marked as Held.
    """
    agm = frappe.get_doc("Annual General Meeting", agm_name)

    if not agm.resolutions:
        return {"sent": 0, "message": "No resolutions recorded."}

    passed = [r for r in agm.resolutions if r.result == "Passed" and r.responsible_officer]
    if not passed:
        return {"sent": 0, "message": "No passed resolutions with responsible officers."}

    # Group by responsible officer
    by_officer = {}
    for res in passed:
        by_officer.setdefault(res.responsible_officer, []).append(res)

    sent = 0
    for officer, items in by_officer.items():
        email = frappe.db.get_value("Employee", officer,
                                    ["company_email", "personal_email"], as_dict=True)
        if not email:
            continue
        recipient = email.company_email or email.personal_email
        if not recipient:
            continue
        try:
            frappe.sendmail(
                recipients        = [recipient],
                subject           = f"AGM Resolution — Action Required — {agm.company}",
                message           = _build_resolution_alert_html(agm, items, officer),
                reference_doctype = "Annual General Meeting",
                reference_name    = agm_name,
            )
            sent += 1
        except Exception:
            pass

    return {"sent": sent, "message": f"Resolution alerts sent to {sent} officer(s)."}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCHEDULER (runs daily via hooks.py scheduler_events)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_agm_scheduled_notifications():
    """
    Daily scheduler job — sends time-triggered AGM notifications automatically.

    Register in hooks.py:
        scheduler_events = {
            "daily": [
                "ecclesia.api.agm_api.run_agm_scheduled_notifications"
            ]
        }
    """
    today_date = getdate(today())

    active_agms = frappe.db.get_all(
        "Annual General Meeting",
        filters={"status": ["not in", ["Closed", "Cancelled"]]},
        fields=["name", "agm_title", "company", "agm_date", "status",
                "cac_filed", "cac_filing_deadline", "notice_date"],
    )

    triggered = []

    for agm in active_agms:
        agm_date = getdate(agm.agm_date) if agm.agm_date else None
        cac_dl   = getdate(agm.cac_filing_deadline) if agm.cac_filing_deadline else None

        if agm_date:
            days_to_agm = date_diff(agm_date, today_date)

            # 21-day notice reminder (if notices not yet sent)
            if days_to_agm == 21 and agm.status == "Planning" and not agm.notice_date:
                triggered.append(f"{agm.name}: 21-day notice trigger")
                _send_internal_alert(
                    agm["name"], agm["company"],
                    "🔔 AGM Notice Due Today",
                    f"The AGM for <b>{agm['company']}</b> is in 21 days ({agm_date}). "
                    f"CAMA 2020 requires notices to be sent TODAY to be compliant. "
                    f"Please dispatch AGM notices immediately via Ecclesia ERP.",
                    level="urgent"
                )

            # 7-day shareholder reminder
            if days_to_agm == 7 and agm.status == "Notices Sent":
                send_agm_reminder(agm["name"], "7_day")
                triggered.append(f"{agm.name}: 7-day reminder sent")

            # Day-of alert to officers
            if days_to_agm == 0:
                send_agm_reminder(agm["name"], "day_of")
                triggered.append(f"{agm.name}: day-of alert sent")

            # Overdue AGM warning (14 days after due date, AGM not yet held)
            if days_to_agm == -14 and agm.status not in ("Held","Minutes Approved","CAC Filed","Closed"):
                _send_internal_alert(
                    agm["name"], agm["company"],
                    "🚨 AGM OVERDUE — CAMA 2020 Breach Risk",
                    f"The AGM for <b>{agm['company']}</b> was due on <b>{agm_date}</b> "
                    f"and has not yet been held (status: {agm['status']}). "
                    f"CAMA 2020 s.438 imposes fines on the company and every officer. "
                    f"Please convene the meeting urgently.",
                    level="critical"
                )
                triggered.append(f"{agm.name}: overdue AGM alert")

        # CAC deadline alerts
        if cac_dl and not agm.cac_filed:
            days_to_cac = date_diff(cac_dl, today_date)
            if days_to_cac in (14, 7, 3, 0, -1):
                send_cac_deadline_alert(agm["name"])
                triggered.append(f"{agm.name}: CAC alert ({days_to_cac} days)")

    frappe.logger().info(f"AGM Scheduler: {len(triggered)} notification(s) triggered: {triggered}")
    return {"triggered": len(triggered), "details": triggered}


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _notify_internal_officers(agm, trigger_type):
    """Send day-of alert to chairperson and company secretary."""
    officers = []
    for field in ["chairperson", "company_secretary"]:
        emp_id = getattr(agm, field, None)
        if emp_id:
            emp = frappe.db.get_value("Employee", emp_id,
                                      ["employee_name", "company_email", "personal_email"], as_dict=True)
            if emp:
                officers.append(emp)

    for emp in officers:
        email = emp.company_email or emp.personal_email
        if not email:
            continue
        frappe.sendmail(
            recipients        = [email],
            subject           = f"📅 AGM is TODAY — {agm.company}",
            message           = _build_day_of_alert_html(agm, emp.employee_name),
            reference_doctype = "Annual General Meeting",
            reference_name    = agm.name,
        )


def _send_internal_alert(agm_name, company, subject, body_html, level="info"):
    """Send an internal alert to System Managers and Accounts Managers."""
    users = frappe.db.get_all(
        "Has Role",
        filters={"role": ["in", ["System Manager", "Accounts Manager"]]},
        fields=["parent"],
        distinct=True,
    )
    emails = []
    for u in users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email and "@" in email:
            emails.append(email)

    if not emails:
        return

    level_colour = {"info": "#3B82F6", "urgent": "#D97706", "critical": "#DC2626"}.get(level, "#3B82F6")
    level_icon   = {"info": "ℹ️", "urgent": "⚠️", "critical": "🚨"}.get(level, "ℹ️")

    html = f"""
    {_email_header(company)}
    <div style="background:#FEF3C7;border-left:5px solid {level_colour};
                padding:16px 20px;margin-bottom:24px;border-radius:0 8px 8px 0">
        <div style="font-size:18px;font-weight:700;color:{level_colour};margin-bottom:8px">
            {level_icon} {subject}
        </div>
        <div style="font-size:14px;color:#1E293B;line-height:1.7">{body_html}</div>
    </div>
    <div style="text-align:center;margin:24px 0">
        <a href="/app/annual-general-meeting/{agm_name}"
           style="background:#1E3A5F;color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            Open AGM Record →
        </a>
    </div>
    {_email_footer()}
    """

    for email in set(emails):
        try:
            frappe.sendmail(
                recipients        = [email],
                subject           = f"{level_icon} {subject} — {company}",
                message           = html,
                reference_doctype = "Annual General Meeting",
                reference_name    = agm_name,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  HTML EMAIL TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

def _email_header(company, subtitle=""):
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F0F4F8;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:620px;margin:32px auto;background:#ffffff;border-radius:12px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">

  <!-- Header Banner -->
  <div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);padding:32px 40px;text-align:center">
    <div style="display:inline-block;background:rgba(255,255,255,0.15);
                border-radius:50%;width:56px;height:56px;line-height:56px;
                font-size:28px;margin-bottom:12px">🏛️</div>
    <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px">
        {company}
    </h1>
    {"" if not subtitle else f'<p style="margin:6px 0 0;color:#93C5FD;font-size:13px">{subtitle}</p>'}
  </div>

  <!-- Body -->
  <div style="padding:32px 40px">
"""


def _email_footer():
    return """
  </div>

  <!-- Footer -->
  <div style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:20px 40px;text-align:center">
    <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.7">
        This communication is issued under CAMA 2020 and the Company's Articles of Association.<br>
        If you believe you received this in error, please contact the Company Secretary.<br>
        <span style="color:#CBD5E1">Powered by Ecclesia ERP &bull; Value Impacts Consulting</span>
    </p>
  </div>

</div>
</body>
</html>
"""


def _info_row(label, value, highlight=False):
    bg = "#EFF6FF" if highlight else "#F8FAFC"
    return f"""
    <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#64748B;font-size:13px;font-weight:600;width:160px;
                   background:{bg}">{label}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#1E293B;font-size:13px;background:{bg}"><b>{value}</b></td>
    </tr>"""


def _agenda_list(agm):
    if not agm.agenda_items:
        return "<p style='color:#64748B;font-size:13px'>Agenda to follow.</p>"
    items = sorted(agm.agenda_items, key=lambda x: x.item_no or 0)
    rows = "".join(
        f"""<tr>
            <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;
                       color:#3B82F6;font-weight:700;font-size:13px;width:40px">{a.item_no}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;
                       color:#1E293B;font-size:13px">{a.agenda_title}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;
                       color:#64748B;font-size:11px">{a.agenda_type}</td>
        </tr>"""
        for a in items
    )
    return f"""
    <table style="width:100%;border-collapse:collapse;border:1px solid #E2E8F0;border-radius:8px;overflow:hidden">
        <thead>
            <tr style="background:#1E3A5F">
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">#</th>
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Agenda Item</th>
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Type</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""


def _notice_badge(days_to, min_days):
    if days_to >= min_days:
        return (f'<span style="background:#D1FAE5;color:#059669;padding:4px 12px;'
                f'border-radius:20px;font-size:12px;font-weight:700">✅ {days_to} days notice — CAMA Compliant</span>')
    return (f'<span style="background:#FEE2E2;color:#DC2626;padding:4px 12px;'
            f'border-radius:20px;font-size:12px;font-weight:700">'
            f'⚠️ {days_to} days — Short notice (min {min_days} required)</span>')


# ─── Template 1: Formal AGM Notice ───────────────────────────────────────────

def _build_agm_notice_html(agm, shareholder_name, days_to, min_notice):
    venue_detail = (
        f"{agm.venue}" if agm.venue_type == "Physical"
        else f"{agm.virtual_platform or 'Online'} — {agm.virtual_link or 'Link to be provided'}"
    )
    mode_icon = "📍" if agm.venue_type == "Physical" else "💻"

    proxy_section = f"""
    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:8px;padding:16px 20px;margin-top:24px">
        <h3 style="margin:0 0 8px;color:#0369A1;font-size:14px">📋 Proxy Appointment</h3>
        <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7">
            A member entitled to attend and vote is entitled to appoint a proxy to attend
            and vote on their behalf. A proxy need not be a member of the Company.<br><br>
            <b>Proxy forms must be returned to the Company Secretary at least 48 hours
            before the time of the meeting.</b><br><br>
            Please download and complete the proxy form attached to this notice.
        </p>
    </div>"""

    return f"""
    {_email_header(agm.company, f"Notice of {agm.agm_type}")}

    <p style="font-size:13px;color:#475569;margin:0 0 20px">Dear <b>{shareholder_name}</b>,</p>

    <p style="font-size:14px;color:#1E293B;line-height:1.7;margin:0 0 20px">
        Notice is hereby given that the <b>{agm.agm_type}</b> of <b>{agm.company}</b>
        will be held on the date and at the time stated below.
    </p>

    <!-- Meeting Details Card -->
    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
                overflow:hidden;margin-bottom:24px">
        <div style="background:#1E3A5F;padding:12px 16px">
            <span style="color:#93C5FD;font-size:12px;font-weight:700;letter-spacing:1px">MEETING DETAILS</span>
        </div>
        <table style="width:100%;border-collapse:collapse">
            {_info_row("📅 Date",  formatdate(agm.agm_date, "long"), highlight=True)}
            {_info_row("🕐 Time",  agm.agm_time or "To be advised")}
            {_info_row(f"{mode_icon} {'Venue' if agm.venue_type=='Physical' else 'Platform'}", venue_detail, highlight=True)}
            {_info_row("📋 Meeting Type", agm.agm_type)}
        </table>
        <div style="padding:12px 16px;background:#FFFBEB;border-top:1px solid #FDE68A">
            {_notice_badge(days_to, min_notice)}
        </div>
    </div>

    <!-- Agenda -->
    <h3 style="color:#1E3A5F;font-size:15px;margin:0 0 12px;padding-bottom:8px;
               border-bottom:2px solid #3B82F6">Agenda</h3>
    {_agenda_list(agm)}

    {proxy_section}

    <!-- CTA -->
    <div style="text-align:center;margin:28px 0 16px">
        <p style="font-size:13px;color:#475569;margin:0 0 16px">
            Please confirm your attendance by replying to this notice or contacting the Company Secretary.
        </p>
    </div>

    <p style="font-size:13px;color:#475569;margin:24px 0 0;line-height:1.7">
        By Order of the Board,<br>
        <b style="color:#1E3A5F">{frappe.db.get_value('Employee', agm.company_secretary, 'employee_name') if agm.company_secretary else 'The Company Secretary'}</b><br>
        Company Secretary<br>
        <b>{agm.company}</b>
    </p>
    <p style="font-size:11px;color:#94A3B8;margin:16px 0 0">
        Date of Notice: {formatdate(today(), "long")}
    </p>

    {_email_footer()}"""


# ─── Template 2: Reminder Email ───────────────────────────────────────────────

def _build_reminder_html(agm, label, when):
    venue_detail = (
        agm.venue if agm.venue_type == "Physical"
        else f"{agm.virtual_platform or 'Online'}: {agm.virtual_link or 'See original notice'}"
    )
    return f"""
    {_email_header(agm.company, f"{agm.agm_type} — {label}")}

    <div style="background:linear-gradient(135deg,#FEF3C7,#FDE68A);border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:36px;margin-bottom:8px">⏰</div>
        <h2 style="margin:0;color:#92400E;font-size:18px">Your AGM is {when}!</h2>
        <p style="margin:8px 0 0;color:#78350F;font-size:13px">
            {agm.agm_type} &bull; {agm.company}
        </p>
    </div>

    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:24px">
        {_info_row("📅 Date", formatdate(agm.agm_date, "long"), highlight=True)}
        {_info_row("🕐 Time", agm.agm_time or "See original notice")}
        {_info_row("📍 Location", venue_detail)}
    </table>

    <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;
                padding:14px 18px;margin-bottom:20px">
        <p style="margin:0;font-size:13px;color:#14532D;line-height:1.7">
            <b>✅ Checklist before the meeting:</b><br>
            &bull; Confirm your attendance or appoint a proxy<br>
            &bull; Review the agenda and financial statements<br>
            &bull; Prepare any questions for the board<br>
            &bull; Submit your proxy form at least 48 hours before the meeting (if applicable)
        </p>
    </div>

    {_email_footer()}"""


# ─── Template 3: Day-of Alert (to officers) ───────────────────────────────────

def _build_day_of_alert_html(agm, officer_name):
    checklist = [
        "Attendance register prepared",
        "Proxy forms collected and validated",
        "Quorum checklist ready",
        "Financial statements distributed",
        "Voting papers prepared (if poll voting)",
        "Minutes template ready",
        "Recording / transcription arranged (if needed)",
    ]
    items = "".join(f"<li style='margin:6px 0;font-size:13px;color:#1E293B'>{c}</li>" for c in checklist)
    return f"""
    {_email_header(agm.company, "AGM Day Checklist")}

    <div style="background:linear-gradient(135deg,#EFF6FF,#DBEAFE);border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:40px;margin-bottom:8px">🏛️</div>
        <h2 style="margin:0;color:#1E40AF;font-size:18px">The AGM is TODAY</h2>
        <p style="margin:8px 0 0;color:#1E3A5F;font-size:13px">Dear <b>{officer_name}</b></p>
    </div>

    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:24px">
        {_info_row("📅 Date",   formatdate(agm.agm_date, "long"), highlight=True)}
        {_info_row("🕐 Time",   agm.agm_time or "—")}
        {_info_row("📍 Venue",  agm.venue or agm.virtual_link or "—")}
        {_info_row("👥 Quorum", f"{agm.quorum_required or 2} members required")}
    </table>

    <h3 style="color:#1E3A5F;font-size:14px;margin:0 0 10px">📋 Pre-Meeting Checklist</h3>
    <ul style="padding-left:20px;margin:0 0 20px">{items}</ul>

    <div style="text-align:center;margin:24px 0">
        <a href="/app/annual-general-meeting/{agm.name}"
           style="background:#1E3A5F;color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            Open AGM Record →
        </a>
    </div>

    {_email_footer()}"""


# ─── Template 4: Proxy Confirmation ──────────────────────────────────────────

def _build_proxy_confirmation_html(agm, proxy):
    return f"""
    {_email_header(agm.company, "Proxy Form Received")}

    <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:36px;margin-bottom:8px">✅</div>
        <h2 style="margin:0;color:#14532D;font-size:17px">Proxy Form Received</h2>
        <p style="margin:8px 0 0;color:#166534;font-size:13px">
            Your proxy appointment has been recorded for the upcoming AGM.
        </p>
    </div>

    <p style="font-size:13px;color:#1E293B;margin:0 0 20px">Dear <b>{proxy.appointing_member}</b>,</p>
    <p style="font-size:13px;color:#475569;line-height:1.7;margin:0 0 20px">
        We confirm receipt of your proxy form for the {agm.agm_type} of <b>{agm.company}</b>.
    </p>

    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:24px">
        {_info_row("📅 Meeting Date",    formatdate(agm.agm_date, "long"), highlight=True)}
        {_info_row("👤 Proxy Appointed", proxy.proxy_name)}
        {_info_row("📊 Shares Held",     f"{proxy.shares_held:,}" if proxy.shares_held else "—")}
        {_info_row("🗳️ Voting Instruction", proxy.voting_instruction or "At Proxy's Discretion")}
        {_info_row("📋 Status",          proxy.status or "Received")}
        {_info_row("📅 Received",        formatdate(proxy.date_received or today(), "long"))}
    </table>

    <div style="background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;
                padding:14px 18px;margin-bottom:20px;font-size:12px;color:#92400E">
        <b>Important:</b> Your proxy, <b>{proxy.proxy_name}</b>, is authorised to attend
        and vote on your behalf at the AGM. If you wish to attend in person, please notify
        the Company Secretary to cancel this proxy at least 24 hours before the meeting.
    </div>

    {_email_footer()}"""


# ─── Template 5: Minutes Approved Notification ───────────────────────────────

def _build_minutes_notification_html(agm):
    resolutions_html = ""
    if agm.resolutions:
        passed = [r for r in agm.resolutions if r.result == "Passed"]
        rows = "".join(
            f"""<tr>
                <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-size:13px;
                           color:#1E3A5F;font-weight:700">{r.resolution_no}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-size:13px">{r.resolution_title}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-size:12px;color:#64748B">{r.resolution_type}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-size:12px">
                    <span style="background:#D1FAE5;color:#059669;padding:2px 8px;border-radius:10px">✅ Passed</span>
                </td>
            </tr>"""
            for r in passed
        )
        resolutions_html = f"""
        <h3 style="color:#1E3A5F;font-size:14px;margin:20px 0 10px;padding-bottom:8px;
                   border-bottom:2px solid #3B82F6">Resolutions Passed</h3>
        <table style="width:100%;border-collapse:collapse;border:1px solid #E2E8F0;border-radius:8px;overflow:hidden">
            <thead><tr style="background:#1E3A5F">
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">#</th>
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Resolution</th>
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Type</th>
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Result</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>"""

    return f"""
    {_email_header(agm.company, "AGM Minutes Approved")}

    <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:36px;margin-bottom:8px">📄</div>
        <h2 style="margin:0;color:#1E40AF;font-size:17px">AGM Minutes Have Been Approved</h2>
    </div>

    <p style="font-size:13px;color:#475569;line-height:1.7;margin:0 0 20px">
        The minutes of the <b>{agm.agm_type}</b> of <b>{agm.company}</b> held on
        <b>{formatdate(agm.agm_date, 'long')}</b> have been approved and signed by the Chairperson
        in accordance with CAMA 2020 s.265.
    </p>

    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:16px">
        {_info_row("📅 Meeting Date",  formatdate(agm.agm_date, "long"), highlight=True)}
        {_info_row("👥 Shareholders Present", str(agm.shareholders_present or "—"))}
        {_info_row("📊 % Shares Represented", f"{flt(agm.quorum_percentage):.1f}%" if agm.quorum_percentage else "—")}
        {_info_row("✅ Quorum",         "Met" if agm.quorum_met else "Not Met")}
    </table>

    {resolutions_html}

    <div style="background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;
                padding:14px 18px;margin-top:20px;font-size:12px;color:#92400E">
        <b>CAC Annual Return:</b> The Company is required to file the Annual Return with the
        Corporate Affairs Commission (CAC) within <b>42 days</b> of this AGM
        (CAMA 2020 s.370). {f"<b>Deadline: {formatdate(agm.cac_filing_deadline, 'long')}</b>" if agm.cac_filing_deadline else ""}
    </div>

    {_email_footer()}"""


# ─── Template 6: CAC Deadline Alert ──────────────────────────────────────────

def _build_cac_alert_html(agm, days_to, is_overdue):
    status_bg    = "#FEE2E2" if is_overdue else "#FEF3C7"
    status_border= "#DC2626" if is_overdue else "#F59E0B"
    status_text  = "#991B1B" if is_overdue else "#92400E"
    status_icon  = "🚨 OVERDUE" if is_overdue else f"⚠️ DUE IN {days_to} DAYS"
    urgency_msg  = (
        f"The CAC Annual Return for <b>{agm.company}</b> is <b>OVERDUE by {abs(days_to)} days</b>. "
        "CAMA 2020 s.438 imposes fines on the company and every officer in default. "
        "<b>File immediately to limit penalty exposure.</b>"
        if is_overdue else
        f"The CAC Annual Return for <b>{agm.company}</b> is due in <b>{days_to} days</b>. "
        "Please ensure filing is completed before the deadline to avoid penalties under CAMA 2020 s.438."
    )
    return f"""
    {_email_header(agm.company, "CAC Annual Return — Action Required")}

    <div style="background:{status_bg};border:2px solid {status_border};border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:36px;margin-bottom:8px">{"🚨" if is_overdue else "⚠️"}</div>
        <h2 style="margin:0;color:{status_text};font-size:18px">{status_icon}</h2>
        <p style="margin:8px 0 0;color:{status_text};font-size:13px">CAC Annual Return Filing</p>
    </div>

    <p style="font-size:14px;color:#1E293B;line-height:1.7;margin:0 0 20px">{urgency_msg}</p>

    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:24px">
        {_info_row("🏛️ Company",          agm.company, highlight=True)}
        {_info_row("📅 AGM Date",          formatdate(agm.agm_date, "long"))}
        {_info_row("📋 CAC Form",          agm.cac_form_type or "CAC 10 — Annual Return")}
        {_info_row("⏰ Filing Deadline",   formatdate(agm.cac_filing_deadline, "long") if agm.cac_filing_deadline else "—", highlight=True)}
        {_info_row("📊 Days " + ("Overdue" if is_overdue else "Remaining"), str(abs(days_to)))}
        {_info_row("💰 Penalty Exposure",  f"₦{flt(agm.cac_penalty_if_late):,.2f}" if agm.cac_penalty_if_late else "See CAMA 2020 s.438")}
    </table>

    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:8px;
                padding:14px 18px;margin-bottom:20px;font-size:13px;color:#1E293B">
        <b>Filing Steps:</b><br>
        1. Log in to the CAC e-Portal (www.cac.gov.ng)<br>
        2. Select Annual Return (Form CAC 10)<br>
        3. Upload signed financial statements and directors' report<br>
        4. Pay the filing fee<br>
        5. Record the CAC Reference Number in Ecclesia ERP
    </div>

    <div style="text-align:center;margin:24px 0">
        <a href="/app/annual-general-meeting/{agm.name}"
           style="background:#DC2626;color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            Record CAC Filing →
        </a>
    </div>

    {_email_footer()}"""


# ─── Template 7: Resolution Implementation Alert ─────────────────────────────

def _build_resolution_alert_html(agm, resolutions, officer_id):
    officer_name = frappe.db.get_value("Employee", officer_id, "employee_name") or officer_id
    rows = "".join(
        f"""<tr>
            <td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;
                       color:#1E3A5F;font-weight:700;font-size:13px">{r.resolution_no}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;font-size:13px">{r.resolution_title}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;font-size:12px;color:#64748B">
                {formatdate(r.implementation_deadline, 'long') if r.implementation_deadline else 'As soon as practicable'}
            </td>
        </tr>"""
        for r in resolutions
    )
    return f"""
    {_email_header(agm.company, "AGM Resolution — Action Required")}

    <p style="font-size:13px;color:#1E293B;margin:0 0 20px">
        Dear <b>{officer_name}</b>,
    </p>

    <p style="font-size:13px;color:#475569;line-height:1.7;margin:0 0 20px">
        The following resolution(s) passed at the <b>{agm.agm_type}</b> of <b>{agm.company}</b>
        held on <b>{formatdate(agm.agm_date, 'long')}</b> require your attention and action.
    </p>

    <table style="width:100%;border-collapse:collapse;border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;margin-bottom:24px">
        <thead><tr style="background:#1E3A5F">
            <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">#</th>
            <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Resolution</th>
            <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Implementation By</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    <div style="background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;
                padding:14px 18px;margin-bottom:20px;font-size:13px;color:#92400E">
        <b>Important:</b> Resolutions passed at a general meeting are binding on the company.
        Please ensure timely implementation and update the AGM record in Ecclesia ERP
        once completed.
    </div>

    <div style="text-align:center;margin:24px 0">
        <a href="/app/annual-general-meeting/{agm.name}"
           style="background:#1E3A5F;color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            View AGM Record →
        </a>
    </div>

    {_email_footer()}"""