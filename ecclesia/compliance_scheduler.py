# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/compliance_scheduler.py
"""
Compliance Scheduler
═══════════════════
All scheduled compliance jobs.

Add to hooks.py:
    scheduler_events = {
        "daily": [
            "ecclesia.ecclesia.compliance_scheduler.run_daily",
        ],
        "weekly": [
            "ecclesia.ecclesia.compliance_scheduler.run_weekly",
        ],
        "monthly": [
            "ecclesia.ecclesia.compliance_scheduler.run_monthly",
        ],
        "yearly": [
            "ecclesia.ecclesia.compliance_scheduler.run_yearly",
        ],
    }

Also add to doc_events in hooks.py:
    doc_events = {
        "Sales Invoice": {
            "on_submit": "ecclesia.api.compliance.liability_engine.post_vat_liability_from_invoice",
        },
        "Purchase Invoice": {
            "on_submit": "ecclesia.api.compliance.liability_engine.post_wht_from_purchase_invoice",
        },
        "Payments": {
            "on_submit": "ecclesia.api.compliance.allocation_engine.on_payments_submit",
        },
    }
"""

import frappe
from frappe.utils import flt, nowdate, getdate, date_diff, add_days


# ── Daily: update license statuses, flag overdue CLL, send reminders ────────

def run_daily():
    frappe.logger().info("Compliance Scheduler: daily run started")
    try:
        _update_license_statuses()
        _flag_overdue_cll_entries()
        _send_upcoming_reminders()
        _run_liability_generation_for_current_month()
    except Exception as e:
        frappe.log_error(f"Compliance daily scheduler error: {e}", "Compliance Scheduler")


def _update_license_statuses():
    """Recalculate days_to_expiry and status for all active licenses."""
    licenses = frappe.get_all(
        "License and Permit",
        filters={"status": ["not in", ["Revoked", "Suspended"]]},
        fields=["name", "expiry_date", "status"]
    )
    today = nowdate()
    for lic in licenses:
        if not lic.expiry_date:
            continue
        days = date_diff(lic.expiry_date, today)
        new_status = lic.status
        if days < 0:
            new_status = "Expired"
        elif days <= 30:
            new_status = "Expiring Soon"
        elif lic.status in ("Expiring Soon", "Expired"):
            new_status = "Valid"

        if new_status != lic.status or True:  # always update days_to_expiry
            frappe.db.set_value("License and Permit", lic.name, {
                "status": new_status,
                "days_to_expiry": days
            }, update_modified=False)

    frappe.db.commit()


def _flag_overdue_cll_entries():
    """Mark CLL entries overdue and compute penalties."""
    today = nowdate()
    overdue = frappe.db.sql("""
        SELECT name FROM `tabCompliance Liability Ledger`
        WHERE status IN ('Open', 'Part Paid')
          AND due_date < %s
          AND balance > 0
    """, (today,), pluck="name")

    for name in overdue:
        try:
            doc = frappe.get_doc("Compliance Liability Ledger", name)
            doc._compute_status()
            doc._compute_penalty()
            doc.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error flagging overdue CLL {name}: {e}")

    if overdue:
        frappe.db.commit()
        frappe.logger().info(f"Compliance Scheduler: flagged {len(overdue)} overdue CLL entries")


def _send_upcoming_reminders():
    """
    Send email reminders for CLL entries / compliance calendar lines due soon.
    Reads reminder_days_before from Compliance Requirement.
    """
    # Find calendar lines due in reminder window and not yet reminded
    reminders = frappe.db.sql("""
        SELECT cl.name, cl.obligation_type, cl.fiscal_month, cl.due_date,
               cl.assigned_to, cr.reminder_days_before, cr.responsible_officer,
               cr.escalation_days_before, cr.requirement_name
        FROM `tabCompliance Calendar Line` cl
        JOIN `tabCompliance Requirement` cr ON cr.name = cl.requirement
        JOIN `tabCompliance Calendar` cc ON cc.name = cl.parent
        WHERE cl.status = 'Pending'
          AND cl.reminder_sent = 0
          AND DATEDIFF(cl.due_date, CURDATE()) <= COALESCE(cr.reminder_days_before, 7)
          AND DATEDIFF(cl.due_date, CURDATE()) >= 0
        LIMIT 200
    """, as_dict=True)

    for rem in reminders:
        _send_compliance_reminder(rem)
        frappe.db.set_value("Compliance Calendar Line", rem.name, "reminder_sent", 1, update_modified=False)

    if reminders:
        frappe.db.commit()


def _send_compliance_reminder(rem):
    """Send email reminder for a specific compliance calendar line."""
    days_left = date_diff(rem.due_date, nowdate())
    recipients = []

    if rem.assigned_to:
        email = frappe.db.get_value("Employee", rem.assigned_to, "company_email")
        if email:
            recipients.append(email)

    if rem.responsible_officer:
        email = frappe.db.get_value("Employee", rem.responsible_officer, "company_email")
        if email and email not in recipients:
            recipients.append(email)

    if not recipients:
        return

    frappe.sendmail(
        recipients=recipients,
        subject=f"Compliance Reminder: {rem.requirement_name} — Due {rem.due_date}",
        message=(
            f"This is a reminder that <b>{rem.requirement_name}</b> for period "
            f"<b>{rem.fiscal_month}</b> is due in <b>{days_left} day(s)</b> "
            f"on <b>{rem.due_date}</b>.<br><br>"
            f"Obligation type: {rem.obligation_type}<br>"
            f"Please ensure filing and payment are completed on time.<br><br>"
            f"<a href='/app/compliance-calendar'>Open Compliance Calendar</a>"
        )
    )


def _run_liability_generation_for_current_month():
    """Run VAT, WHT, Payroll liability generation for current month."""
    from ecclesia.api.compliance.liability_engine import run_all_liability_generation
    d = getdate(nowdate())
    fiscal_month = f"{d.year:04d}-{d.month:02d}"
    try:
        run_all_liability_generation(fiscal_month)
    except Exception as e:
        frappe.log_error(f"Daily liability generation failed: {e}", "Compliance Scheduler")


# ── Weekly: calendar line status sync, expired license incidents ────────────

def run_weekly():
    frappe.logger().info("Compliance Scheduler: weekly run")
    try:
        _sync_calendar_line_statuses()
        _raise_incidents_for_expired_licenses()
    except Exception as e:
        frappe.log_error(f"Compliance weekly scheduler error: {e}", "Compliance Scheduler")


def _sync_calendar_line_statuses():
    """Update calendar line statuses from linked filing docs."""
    lines_with_filing = frappe.db.sql("""
        SELECT cl.name, cf.status AS filing_status
        FROM `tabCompliance Calendar Line` cl
        JOIN `tabCompliance Filing` cf ON cf.name = cl.filing_reference
        WHERE cl.status NOT IN ('Filed', 'Cancelled')
          AND cf.docstatus = 1
    """, as_dict=True)

    for row in lines_with_filing:
        new_status = "Filed" if row.filing_status in ("Submitted to Authority", "Accepted") else "In Progress"
        frappe.db.set_value("Compliance Calendar Line", row.name, "status", new_status, update_modified=False)

    # Mark overdue
    frappe.db.sql("""
        UPDATE `tabCompliance Calendar Line`
        SET status = 'Overdue'
        WHERE status = 'Pending'
          AND due_date < CURDATE()
    """)
    frappe.db.commit()


def _raise_incidents_for_expired_licenses():
    """Create a Compliance Incident for any newly-expired license."""
    expired = frappe.get_all(
        "License and Permit",
        filters={"status": "Expired"},
        fields=["name", "license_name", "license_type", "expiry_date", "company"]
    )
    for lic in expired:
        incident_title = f"Expired License: {lic.license_name}"
        if not frappe.db.exists("Compliance Incident", {"incident_title": incident_title, "status": ["!=", "Closed"]}):
            inc = frappe.new_doc("Compliance Incident")
            inc.incident_title  = incident_title
            inc.incident_date   = nowdate()
            inc.incident_type   = "Expired License"
            inc.obligation_type = "License"
            inc.severity        = "Major"
            inc.status          = "Reported"
            inc.description     = (
                f"License '{lic.license_name}' ({lic.license_type}) expired on {lic.expiry_date}. "
                f"Please renew immediately to avoid regulatory sanctions."
            )
            inc.insert(ignore_permissions=True)

    if expired:
        frappe.db.commit()


# ── Monthly: ITF assessment, compliance KPI snapshot ────────────────────────

def run_monthly():
    frappe.logger().info("Compliance Scheduler: monthly run")
    try:
        _take_compliance_kpi_snapshot()
    except Exception as e:
        frappe.log_error(f"Compliance monthly scheduler error: {e}", "Compliance Scheduler")


def _take_compliance_kpi_snapshot():
    """
    Compute and store monthly KPIs for compliance dashboard.
    Stored in a simple `Compliance KPI Log` (can be a simple DB table or existing DocType).
    """
    today = getdate(nowdate())
    fiscal_month = f"{today.year:04d}-{today.month:02d}"
    companies = frappe.db.get_all("Company", filters={"is_group": 0}, pluck="name")

    for company in companies:
        _compute_company_kpis(company, fiscal_month)


def _compute_company_kpis(company, fiscal_month):
    """Return a KPI dict for a company/month and log to console (extend to custom DocType as needed)."""
    total   = frappe.db.count("Compliance Liability Ledger", {"company": company})
    paid    = frappe.db.count("Compliance Liability Ledger", {"company": company, "status": "Paid"})
    overdue = frappe.db.count("Compliance Liability Ledger", {"company": company, "status": "Overdue"})
    part    = frappe.db.count("Compliance Liability Ledger", {"company": company, "status": "Part Paid"})

    licenses_expired  = frappe.db.count("License and Permit", {"company": company, "status": "Expired"})
    licenses_expiring = frappe.db.count("License and Permit", {"company": company, "status": "Expiring Soon"})

    open_incidents = frappe.db.count("Compliance Incident", {
        "status": ["not in", ["Resolved", "Closed"]]
    })

    compliance_score = round((paid / total * 100), 1) if total else 100.0

    frappe.logger().info(
        f"ComplianceKPI | {company} | {fiscal_month} | Score: {compliance_score}% | "
        f"Paid: {paid}/{total} | Overdue: {overdue} | Incidents: {open_incidents} | "
        f"Expired licenses: {licenses_expired}"
    )
    return {
        "company": company, "fiscal_month": fiscal_month,
        "compliance_score": compliance_score,
        "total_cll": total, "paid_cll": paid, "overdue_cll": overdue, "part_paid_cll": part,
        "expired_licenses": licenses_expired, "expiring_licenses": licenses_expiring,
        "open_incidents": open_incidents
    }


# ── Yearly: ITF generation ───────────────────────────────────────────────────

def run_yearly():
    frappe.logger().info("Compliance Scheduler: annual run — ITF generation")
    from ecclesia.api.compliance.liability_engine import run_itf_generation
    today = getdate(nowdate())
    fiscal_year = str(today.year)
    companies = frappe.db.get_all("Company", filters={"is_group": 0}, pluck="name")
    for company in companies:
        try:
            run_itf_generation(company, fiscal_year)
        except Exception as e:
            frappe.log_error(f"ITF generation failed for {company}: {e}", "Compliance Scheduler")