# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/documents_api.py
"""
Documents, Filing & Legal Register API
==========================================
Whitelisted methods:
    get_document_dashboard_stats(company)
    get_expiring_items(company, days_ahead)
    record_legal_register_renewal(legal_register_name, renewal_date, new_expiry_date, renewed_by, cost)
    send_expiry_alert(doctype_name, doctype="Legal Register")
    run_document_scheduled_notifications()   ← called by scheduler
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff, cint, formatdate

from ecclesia.utils.email_templates import email_header, email_footer, info_row, cta_button, get_officer_email


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_document_dashboard_stats(company=None):
	filters = {"company": company} if company else {}

	legal = frappe.db.get_all("Legal Register", filters=filters,
		fields=["name", "status", "is_expired", "is_expiring_soon", "compliance_status"])
	docs = frappe.db.get_all("Corporate Document", filters=filters,
		fields=["name", "status", "is_expiring_soon", "confidential"])
	seals = frappe.db.get_all("Company Seal Register", filters=filters, fields=["name", "status"])

	return {
		"legal_total": len(legal),
		"legal_active": sum(1 for l in legal if l.status == "Active"),
		"legal_expiring_soon": sum(1 for l in legal if l.is_expiring_soon),
		"legal_expired": sum(1 for l in legal if l.is_expired),
		"legal_non_compliant": sum(1 for l in legal if l.compliance_status == "Non-Compliant"),
		"documents_total": len(docs),
		"documents_expiring_soon": sum(1 for d in docs if d.is_expiring_soon),
		"documents_confidential": sum(1 for d in docs if d.confidential),
		"seal_requests_pending": sum(1 for s in seals if s.status == "Requested"),
	}


@frappe.whitelist()
def get_expiring_items(company=None, days_ahead=60):
	"""Unified expiry feed across Legal Register and Corporate Document, for the dashboard."""
	today_date = getdate(today())
	results = []

	legal = frappe.db.get_all(
		"Legal Register",
		filters={**({"company": company} if company else {}), "status": ["not in", ["Renewed"]]},
		fields=["name", "instrument_title", "expiry_date", "issuing_authority", "responsible_officer"],
	)
	for l in legal:
		if not l.expiry_date:
			continue
		days_to = date_diff(getdate(l.expiry_date), today_date)
		if days_to <= int(days_ahead):
			results.append({
				"source": "Legal Register", "name": l.name, "title": l.instrument_title,
				"expiry_date": l.expiry_date, "days_to": days_to,
				"owner": l.responsible_officer, "detail": l.issuing_authority,
				"alert_level": "red" if days_to < 0 else "amber" if days_to <= 14 else "green",
			})

	docs = frappe.db.get_all(
		"Corporate Document",
		filters={**({"company": company} if company else {}), "status": ["not in", ["Superseded", "Archived"]]},
		fields=["name", "document_title", "expiry_date", "document_type", "document_owner"],
	)
	for d in docs:
		if not d.expiry_date:
			continue
		days_to = date_diff(getdate(d.expiry_date), today_date)
		if days_to <= int(days_ahead):
			results.append({
				"source": "Corporate Document", "name": d.name, "title": d.document_title,
				"expiry_date": d.expiry_date, "days_to": days_to,
				"owner": d.document_owner, "detail": d.document_type,
				"alert_level": "red" if days_to < 0 else "amber" if days_to <= 14 else "green",
			})

	return sorted(results, key=lambda x: x["days_to"])


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def record_legal_register_renewal(legal_register_name, renewal_date, new_expiry_date, renewed_by=None, cost=None):
	doc = frappe.get_doc("Legal Register", legal_register_name)
	doc.add_renewal(renewal_date, new_expiry_date, renewed_by, cost)
	return {"message": f"Renewal recorded. New expiry: {formatdate(new_expiry_date, 'long')}."}


@frappe.whitelist()
def send_expiry_alert(doctype_name, doctype="Legal Register"):
	if doctype not in ("Legal Register", "Corporate Document"):
		frappe.throw(_("Unsupported doctype for expiry alert."))
	doc = frappe.get_doc(doctype, doctype_name)
	_send_expiry_email(doc, doctype)
	return {"message": "Expiry alert sent."}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_document_scheduled_notifications():
	"""
	Daily scheduler job.

	Register in hooks.py:
	    scheduler_events = {
	        "daily": [
	            "ecclesia.api.documents_api.run_document_scheduled_notifications"
	        ]
	    }
	"""
	today_date = getdate(today())
	triggered = []

	legal_items = frappe.db.get_all(
		"Legal Register",
		filters={"status": ["not in", ["Renewed", "Lapsed"]]},
		fields=["name", "expiry_date", "responsible_officer"],
	)
	for item in legal_items:
		if not item.expiry_date:
			continue
		days_to = date_diff(getdate(item.expiry_date), today_date)
		if days_to in (60, 30, 14, 7, 0, -7):
			doc = frappe.get_doc("Legal Register", item.name)
			_send_expiry_email(doc, "Legal Register")
			triggered.append(f"{item.name}: expiry alert (day {days_to})")

	doc_items = frappe.db.get_all(
		"Corporate Document",
		filters={"status": ["not in", ["Superseded", "Archived"]]},
		fields=["name", "expiry_date", "review_date", "document_owner"],
	)
	for item in doc_items:
		for date_field, label in (("expiry_date", "expiry"), ("review_date", "review")):
			d = item.get(date_field)
			if not d:
				continue
			days_to = date_diff(getdate(d), today_date)
			if days_to in (30, 7, 0):
				doc = frappe.get_doc("Corporate Document", item.name)
				_send_expiry_email(doc, "Corporate Document", label=label)
				triggered.append(f"{item.name}: {label} alert (day {days_to})")

	frappe.logger().info(f"Documents Scheduler: {len(triggered)} notification(s) triggered: {triggered}")
	return {"triggered": len(triggered), "details": triggered}


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _send_expiry_email(doc, doctype, label="expiry"):
	if doctype == "Legal Register":
		title, owner_field, date_field = doc.instrument_title, "responsible_officer", "expiry_date"
	else:
		title, owner_field, date_field = doc.document_title, "document_owner", "expiry_date" if label == "expiry" else "review_date"

	owner = getattr(doc, owner_field, None)
	email = get_officer_email(owner)
	relevant_date = getattr(doc, date_field, None)
	if not relevant_date:
		return

	days_to = date_diff(getdate(relevant_date), getdate(today()))
	is_overdue = days_to < 0

	recipients = []
	if email:
		recipients.append(email)
	if is_overdue or (doctype == "Legal Register"):
		users = frappe.db.get_all(
			"Has Role",
			filters={"role": ["in", ["System Manager", "Accounts Manager"]]},
			fields=["parent"], distinct=True,
		)
		for u in users:
			e = frappe.db.get_value("User", u.parent, "email")
			if e and "@" in e and e not in recipients:
				recipients.append(e)

	if not recipients:
		return

	verb = "OVERDUE" if is_overdue else f"due in {days_to} days"
	html = f"""
    {email_header(doc.company, f"{doctype} — {label.title()} Alert")}
    <div style="background:{'#FEE2E2' if is_overdue else '#FEF3C7'};
                border:2px solid {'#DC2626' if is_overdue else '#F59E0B'};
                border-radius:10px;padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:36px;margin-bottom:8px">{'🚨' if is_overdue else '⚠️'}</div>
        <h2 style="margin:0;color:{'#991B1B' if is_overdue else '#92400E'};font-size:18px">
            {title} — {verb.upper()}
        </h2>
    </div>
    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden">
        {info_row(label.title() + " Date", formatdate(relevant_date, "long"), highlight=True)}
        {info_row("Record", doctype)}
    </table>
    {cta_button(f"/app/{doctype.lower().replace(' ', '-')}/{doc.name}", "Open Record",
                colour="#DC2626" if is_overdue else "#1E3A5F")}
    {email_footer()}
    """
	for r in recipients:
		try:
			frappe.sendmail(
				recipients=[r],
				subject=f"{'🚨' if is_overdue else '⚠️'} {title} — {verb}",
				message=html,
				reference_doctype=doctype,
				reference_name=doc.name,
			)
		except Exception:
			pass
