# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/compliance_scheduler_v2.py
"""
Compliance Scheduler v2 — data-driven alerts from Compliance Alert Rule DocType.

hooks.py scheduler_events:
    "daily":   ["ecclesia.ecclesia.compliance_scheduler_v2.run_daily"],
    "monthly": ["ecclesia.ecclesia.compliance_scheduler_v2.run_monthly"],
    "yearly":  ["ecclesia.ecclesia.compliance_scheduler_v2.run_yearly"],

hooks.py doc_events:
    "Sales Invoice":  {"on_submit": "ecclesia.api.compliance.liability_engine_v2.generate_vat_liability_from_doc"},
    "Payments":       {"on_submit": "ecclesia.api.compliance.allocation_engine_v2.on_payments_submit"},
"""

import frappe
from frappe.utils import flt, nowdate, getdate, date_diff, add_days


def run_daily():
    _update_license_statuses()
    _flag_overdue_cll()
    _fire_alert_rules()
    _generate_current_month_liabilities()
    _take_kpi_snapshot()


def run_monthly():
    """Already handled by daily; monthly hook for heavier operations."""
    pass


def run_yearly():
    """ITF annual assessment."""
    from ecclesia.api.compliance.liability_engine_v2 import _period_label
    from frappe.utils import getdate, nowdate
    d = getdate(nowdate())
    companies = frappe.db.get_all("Company", filters={"is_group":0}, pluck="name")
    for company in companies:
        try:
            _generate_itf_annual(company, d.year)
        except Exception as e:
            frappe.log_error(f"ITF annual {company}: {e}")


# ── License Status Update ──────────────────────────────────────────────────────

def _update_license_statuses():
    licenses = frappe.db.get_all("License Management",
        filters={"auto_status_update":1, "status":["not in",["Suspended","Revoked"]]},
        fields=["name","current_expiry_date","status"])
    today = nowdate()
    for lic in licenses:
        if not lic.current_expiry_date:
            continue
        days = date_diff(lic.current_expiry_date, today)
        new_status = "Active" if days > 30 else "Expiring Soon" if days >= 0 else "Expired"
        if new_status != lic.status:
            frappe.db.set_value("License Management", lic.name,
                {"status": new_status, "days_to_expiry": days}, update_modified=False)
    frappe.db.commit()


# ── Overdue CLL Flagging ───────────────────────────────────────────────────────

def _flag_overdue_cll():
    today = nowdate()
    overdue = frappe.db.sql("""
        SELECT name FROM `tabCompliance Liability Ledger`
        WHERE status IN ('Open','Partially Paid')
          AND due_date < %s AND balance_due > 0
    """, (today,), pluck="name")
    for name in overdue:
        doc = frappe.get_doc("Compliance Liability Ledger", name)
        doc._compute_status()
        doc._compute_penalty()
        doc.save(ignore_permissions=True)
    if overdue:
        frappe.db.commit()


# ── Alert Rules Engine ─────────────────────────────────────────────────────────

def _fire_alert_rules():
    """
    Read all active Compliance Alert Rules and send notifications.
    This makes the alert system data-driven — no hardcoded scheduler logic.
    """
    rules = frappe.get_all("Compliance Alert Rule",
        filters={"active":1},
        fields=["name","alert_name","trigger_type","obligation_type","days_before_event",
                "channel","recipient_role","recipient_employee","message_template",
                "escalate_if_unresolved","escalation_days"])

    for rule in rules:
        try:
            if rule.trigger_type == "Due Date Approaching":
                _alert_due_date(rule)
            elif rule.trigger_type == "Overdue":
                _alert_overdue(rule)
            elif rule.trigger_type == "License Expiry":
                _alert_license_expiry(rule)
        except Exception as e:
            frappe.log_error(f"Alert rule {rule.name} failed: {e}", "Compliance Alert")


def _get_recipients(rule):
    emails = []
    if rule.recipient_employee:
        email = frappe.db.get_value("Employee", rule.recipient_employee, "company_email")
        if email: emails.append(email)
    if rule.recipient_role:
        users = frappe.db.get_all("Has Role", filters={"role": rule.recipient_role}, fields=["parent"])
        for u in users:
            e = frappe.db.get_value("User", u.parent, "email")
            if e and e not in emails: emails.append(e)
    return emails


def _alert_due_date(rule):
    days = int(rule.days_before_event or 7)
    target_date = add_days(nowdate(), days)
    filters = {"due_date": target_date, "status": ["in", ["Open","Partially Paid"]]}
    if rule.obligation_type and rule.obligation_type != "All":
        filters["obligation_type"] = rule.obligation_type
    clls = frappe.get_all("Compliance Liability Ledger", filters=filters,
                           fields=["name","obligation_type","period_label","due_date","company","balance_due"])
    for cll in clls:
        recipients = _get_recipients(rule)
        if recipients:
            frappe.sendmail(recipients=recipients,
                subject=f"⚠️ Compliance Due in {days} Days: {cll.obligation_type} {cll.period_label}",
                message=(f"<b>{cll.obligation_type}</b> for <b>{cll.period_label}</b> ({cll.company})<br>"
                         f"Balance due: ₦{flt(cll.balance_due):,.0f}<br>"
                         f"Due date: <b>{cll.due_date}</b><br>"
                         f"<a href='/Form/Compliance Liability Ledger/{cll.name}'>View CLL</a>"))


def _alert_overdue(rule):
    filters = {"status": "Overdue", "balance_due": [">", 0]}
    if rule.obligation_type and rule.obligation_type != "All":
        filters["obligation_type"] = rule.obligation_type
    clls = frappe.get_all("Compliance Liability Ledger", filters=filters,
                           fields=["name","obligation_type","period_label","due_date","company","balance_due","penalty_amount"])
    if not clls:
        return
    recipients = _get_recipients(rule)
    if recipients:
        items = "\n".join([f"- {c.obligation_type} {c.period_label} ({c.company}): "
                           f"Balance ₦{flt(c.balance_due):,.0f} | Penalty ₦{flt(c.penalty_amount):,.0f}"
                           for c in clls])
        frappe.sendmail(recipients=recipients,
            subject=f"🚨 {len(clls)} Overdue Compliance Obligation(s)",
            message=f"The following obligations are OVERDUE:<br><pre>{items}</pre>")


def _alert_license_expiry(rule):
    days = int(rule.days_before_event or 30)
    licenses = frappe.db.sql("""
        SELECT name, license_name, current_expiry_date, days_to_expiry, company
        FROM `tabLicense Management`
        WHERE days_to_expiry <= %s AND days_to_expiry >= 0
          AND status NOT IN ('Suspended','Revoked')
    """, (days,), as_dict=True)
    if not licenses:
        return
    recipients = _get_recipients(rule)
    if recipients:
        items = "\n".join([f"- {l.license_name} ({l.company}): expires {l.current_expiry_date} ({l.days_to_expiry}d)" for l in licenses])
        frappe.sendmail(recipients=recipients,
            subject=f"⚠️ {len(licenses)} License(s) Expiring Within {days} Days",
            message=f"The following licenses are expiring soon:<br><pre>{items}</pre>")


# ── Liability Generation ───────────────────────────────────────────────────────

def _generate_current_month_liabilities():
    from ecclesia.api.compliance.liability_engine_v2 import run_all_liability_generation, _period_label
    try:
        run_all_liability_generation(_period_label())
    except Exception as e:
        frappe.log_error(f"Daily liability generation: {e}", "Compliance Scheduler v2")


def _generate_itf_annual(company, year):
    annual_payroll = frappe.db.sql("""
        SELECT COALESCE(SUM(gross_pay),0) FROM `tabSalary Slip`
        WHERE company=%s AND docstatus=1 AND YEAR(start_date)=%s
    """, (company, year))[0][0]
    if not annual_payroll:
        return
    itf_levy    = flt(annual_payroll) * 0.01
    period_label = f"04-{year+1}"  # ITF due April of following year
    from ecclesia.api.compliance.liability_engine_v2 import _get_or_create_cll
    cll = _get_or_create_cll(company, "ITF", period_label)
    cll.append("source_lines", {
        "source_doctype":"Payroll Entry","source_document":f"Annual-{year}",
        "posting_date":f"{year}-12-31","gross_amount":annual_payroll,"liability_amount":itf_levy,"rate_applied":1.0
    })
    cll.save(ignore_permissions=True)
    frappe.db.commit()


# ── KPI Snapshot ───────────────────────────────────────────────────────────────

def _take_kpi_snapshot():
    from frappe.utils import getdate, nowdate
    d = getdate(nowdate())
    period_label = f"{d.month:02d}-{d.year:04d}"
    companies = frappe.db.get_all("Company", filters={"is_group":0}, pluck="name")

    for company in companies:
        try:
            _snapshot_company(company, period_label)
        except Exception as e:
            frappe.log_error(f"KPI snapshot {company}: {e}")


def _snapshot_company(company, period_label):
    """Upsert a Compliance KPI Snapshot for today."""
    existing = frappe.db.get_value("Compliance KPI Snapshot",
        {"company": company, "period": period_label}, "name")

    total   = flt(frappe.db.sql("SELECT COALESCE(SUM(total_liability),0) FROM `tabCompliance Liability Ledger` WHERE company=%s AND period_label=%s",(company,period_label))[0][0])
    paid    = flt(frappe.db.sql("SELECT COALESCE(SUM(total_allocated),0) FROM `tabCompliance Liability Ledger` WHERE company=%s AND period_label=%s",(company,period_label))[0][0])
    penalty = flt(frappe.db.sql("SELECT COALESCE(SUM(penalty_amount),0) FROM `tabCompliance Liability Ledger` WHERE company=%s AND status='Overdue'",(company,))[0][0])
    total_cll   = frappe.db.count("Compliance Liability Ledger", {"company":company})
    paid_cll    = frappe.db.count("Compliance Liability Ledger", {"company":company,"status":"Fully Paid"})
    exp_lic     = frappe.db.count("License Management", {"company":company,"status":"Expired"})
    valid_lic   = frappe.db.count("License Management", {"company":company,"status":"Active"})
    total_lic   = frappe.db.count("License Management", {"company":company})
    open_inc    = frappe.db.count("Compliance Incident", {"status":["not in",["Resolved","Closed"]]})
    open_find   = frappe.db.sql("""SELECT COUNT(*) FROM `tabCompliance Audit Finding` caf JOIN `tabCompliance Audit` ca ON ca.name=caf.parent WHERE ca.company=%s AND caf.status='Open'""",(company,))[0][0]

    cll_score = (paid_cll/total_cll*100) if total_cll else 100.0
    lic_score = (valid_lic/total_lic*100) if total_lic else 100.0
    inc_score = max(0, 100 - open_inc * 5)
    score     = round(cll_score*0.5 + lic_score*0.3 + inc_score*0.2, 1)

    # Per-obligation statuses
    def ob_status(ob):
        return frappe.db.get_value("Compliance Liability Ledger",
            {"company":company,"obligation_type":ob,"period_label":period_label},"status") or "Not Generated"

    vals = {
        "company":period_label, "period":period_label, "snapshot_date":nowdate(),
        "total_liability":total,"total_paid":paid,"outstanding":max(0,total-paid),
        "compliance_score":score,"penalty_exposure":penalty,
        "expired_licenses":exp_lic,"open_incidents":open_inc,"open_audit_findings":open_find,
        "vat_status":ob_status("VAT"),"wht_status":ob_status("WHT"),
        "paye_status":ob_status("PAYE"),"pension_status":ob_status("Pension"),
        "nhf_status":ob_status("NHF"),"nsitf_status":ob_status("NSITF"),"itf_status":ob_status("ITF"),
    }

    if existing:
        for k,v in vals.items():
            if k not in ("company","period"):
                frappe.db.set_value("Compliance KPI Snapshot", existing, k, v, update_modified=False)
    else:
        snap = frappe.new_doc("Compliance KPI Snapshot")
        for k,v in vals.items():
            snap.set(k,v)
        snap.company = company
        snap.insert(ignore_permissions=True)

    frappe.db.commit()
