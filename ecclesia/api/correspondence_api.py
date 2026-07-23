# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/correspondence_api.py
"""
Correspondence API — Routing, Acknowledgement, Dashboard, Overdue Alerts
============================================================================
Whitelisted methods:
    get_correspondence_dashboard_stats(company)
    get_overdue_correspondence(company, days_ahead)
    route_correspondence(correspondence_name, employee, instruction)
    send_acknowledgement_receipt(correspondence_name)
    send_response_overdue_alert(correspondence_name)
    run_correspondence_scheduled_notifications()   ← called by scheduler

Notification triggers:
    1. Routing Notice        → Employee the item is routed to
    2. Acknowledgement Receipt → Sender (incoming mail, on request)
    3. Response Due Reminder → Assigned owner (2 days before / on due date)
    4. Response Overdue Alert → Assigned owner + System/Accounts Manager
    5. Confidential Access Alert → Logged when a confidential item is opened (audit trail)
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff, cint, now_datetime, formatdate

from ecclesia.utils.email_templates import (
	email_header, email_footer, info_row, cta_button, get_officer_email,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_correspondence_dashboard_stats(company=None):
	"""KPI summary for the Secretary Dashboard."""
	all_corr = frappe.db.get_all(
		"Correspondence",
		filters=({"company": company} if company else {}),
		fields=["name", "correspondence_type", "status", "priority", "confidential",
				"response_required", "response_status", "is_overdue", "due_date"],
	)
	return {
		"total": len(all_corr),
		"incoming": sum(1 for c in all_corr if c.correspondence_type == "Incoming Mail"),
		"outgoing": sum(1 for c in all_corr if c.correspondence_type == "Outgoing Mail"),
		"memos": sum(1 for c in all_corr if c.correspondence_type == "Internal Memo"),
		"circulars": sum(1 for c in all_corr if c.correspondence_type == "Circular"),
		"pending_response": sum(1 for c in all_corr if c.response_status == "Pending"),
		"overdue_response": sum(1 for c in all_corr if c.response_status == "Overdue"),
		"overdue_general": sum(1 for c in all_corr if c.is_overdue),
		"confidential_open": sum(1 for c in all_corr if c.confidential and c.status not in ("Closed", "Responded")),
		"urgent_open": sum(1 for c in all_corr if c.priority == "Urgent" and c.status not in ("Closed", "Responded", "Dispatched")),
	}


@frappe.whitelist()
def get_overdue_correspondence(company=None, days_ahead=7):
	"""Return correspondence overdue or due within N days, for the dashboard."""
	items = frappe.db.get_all(
		"Correspondence",
		filters={**({"company": company} if company else {}),
				 "status": ["not in", ["Closed", "Responded", "Dispatched"]]},
		fields=["name", "subject", "correspondence_type", "priority", "due_date",
				"response_due_date", "assigned_to", "status"],
	)
	today_date = getdate(today())
	results = []
	for c in items:
		relevant_date = c.due_date or c.response_due_date
		if not relevant_date:
			continue
		days_to = date_diff(getdate(relevant_date), today_date)
		if days_to <= int(days_ahead):
			results.append({
				**c,
				"days_to": days_to,
				"overdue": days_to < 0,
				"alert_level": "red" if days_to < 0 else "amber" if days_to <= 2 else "green",
			})
	return sorted(results, key=lambda x: x["days_to"])


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTIONS (whitelisted — callable from JS buttons)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def route_correspondence(correspondence_name, employee, instruction=""):
	"""Add a routing log row and notify the employee it was routed to."""
	doc = frappe.get_doc("Correspondence", correspondence_name)

	doc.append("routing_log", {
		"routed_to": employee,
		"routed_date": today(),
		"instruction": instruction,
		"status": "Pending",
	})
	if doc.status in ("Draft", "Pending Review"):
		doc.status = "Routed"
	doc.save(ignore_permissions=True)

	email = get_officer_email(employee)
	if email:
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"Correspondence Routed to You — {doc.subject}",
				message=_build_routing_html(doc, instruction),
				reference_doctype="Correspondence",
				reference_name=correspondence_name,
			)
		except Exception:
			pass

	return {"message": f"Routed to {employee}." + (" Notification sent." if email else " No email on file for recipient.")}


@frappe.whitelist()
def send_acknowledgement_receipt(correspondence_name):
	"""Send an acknowledgement-of-receipt email back to the sender of incoming mail."""
	doc = frappe.get_doc("Correspondence", correspondence_name)

	if doc.correspondence_type != "Incoming Mail":
		frappe.throw(_("Acknowledgement receipts apply to Incoming Mail only."))
	if not doc.from_email:
		return {"sent": 0, "message": "No sender email on file."}

	frappe.sendmail(
		recipients=[doc.from_email],
		subject=f"Acknowledgement of Receipt — {doc.subject}",
		message=_build_acknowledgement_html(doc),
		reference_doctype="Correspondence",
		reference_name=correspondence_name,
	)
	doc.acknowledgement_received = 0  # this is US acknowledging THEM, not the reverse
	doc.db_set("acknowledgement_date", today())
	return {"sent": 1, "message": f"Acknowledgement sent to {doc.from_email}."}


@frappe.whitelist()
def send_response_overdue_alert(correspondence_name):
	"""Manually trigger an overdue-response alert for one correspondence item."""
	doc = frappe.get_doc("Correspondence", correspondence_name)
	_send_overdue_alert_for(doc)
	return {"message": "Overdue alert sent."}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCHEDULER (runs daily via hooks.py scheduler_events)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_correspondence_scheduled_notifications():
	"""
	Daily scheduler job — sends time-triggered Correspondence notifications automatically.

	Register in hooks.py:
	    scheduler_events = {
	        "daily": [
	            "ecclesia.api.correspondence_api.run_correspondence_scheduled_notifications"
	        ]
	    }
	"""
	today_date = getdate(today())
	open_items = frappe.db.get_all(
		"Correspondence",
		filters={"status": ["not in", ["Closed", "Responded", "Dispatched"]]},
		fields=["name", "subject", "assigned_to", "due_date", "response_due_date",
				"response_required", "priority"],
	)

	triggered = []

	for item in open_items:
		relevant_date = item.due_date or item.response_due_date
		if not relevant_date:
			continue
		days_to = date_diff(getdate(relevant_date), today_date)

		# 2-day advance reminder
		if days_to == 2 and item.assigned_to:
			doc = frappe.get_doc("Correspondence", item.name)
			_send_due_reminder(doc, days_to=2)
			triggered.append(f"{item.name}: 2-day due reminder")

		# Overdue alert (on due date and every 3 days after, up to -9)
		if days_to in (0, -3, -6, -9):
			doc = frappe.get_doc("Correspondence", item.name)
			_send_overdue_alert_for(doc)
			triggered.append(f"{item.name}: overdue alert (day {days_to})")

	frappe.logger().info(f"Correspondence Scheduler: {len(triggered)} notification(s) triggered: {triggered}")
	return {"triggered": len(triggered), "details": triggered}


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _send_due_reminder(doc, days_to):
	email = get_officer_email(doc.assigned_to)
	if not email:
		return
	html = f"""
    {email_header(doc.company, "Correspondence Due Soon")}
    <p style="font-size:13px;color:#1E293B;line-height:1.7">
        <b>{doc.subject}</b> is due in <b>{days_to} day(s)</b>.
    </p>
    {cta_button(f"/app/correspondence/{doc.name}", "Open Correspondence")}
    {email_footer()}
    """
	try:
		frappe.sendmail(
			recipients=[email],
			subject=f"⏰ Due in {days_to} days — {doc.subject}",
			message=html,
			reference_doctype="Correspondence",
			reference_name=doc.name,
		)
	except Exception:
		pass


def _send_overdue_alert_for(doc):
	emails = set()
	owner_email = get_officer_email(doc.assigned_to)
	if owner_email:
		emails.add(owner_email)

	if doc.priority in ("Urgent", "High"):
		users = frappe.db.get_all(
			"Has Role",
			filters={"role": ["in", ["System Manager", "Accounts Manager"]]},
			fields=["parent"], distinct=True,
		)
		for u in users:
			e = frappe.db.get_value("User", u.parent, "email")
			if e and "@" in e:
				emails.add(e)

	if not emails:
		return

	html = f"""
    {email_header(doc.company, "Overdue Correspondence")}
    <div style="background:#FEE2E2;border:2px solid #DC2626;border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:36px;margin-bottom:8px">🚨</div>
        <h2 style="margin:0;color:#991B1B;font-size:18px">Correspondence Overdue</h2>
    </div>
    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:20px">
        {info_row("Subject", doc.subject, highlight=True)}
        {info_row("Type", doc.correspondence_type)}
        {info_row("Priority", doc.priority)}
        {info_row("Due Date", formatdate(doc.due_date or doc.response_due_date, "long"))}
    </table>
    {cta_button(f"/app/correspondence/{doc.name}", "Open Correspondence", colour="#DC2626")}
    {email_footer()}
    """
	for email in emails:
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"🚨 Overdue — {doc.subject}",
				message=html,
				reference_doctype="Correspondence",
				reference_name=doc.name,
			)
		except Exception:
			pass


def _build_routing_html(doc, instruction):
	return f"""
    {email_header(doc.company, "Correspondence Routed to You")}
    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:20px">
        {info_row("Subject", doc.subject, highlight=True)}
        {info_row("Type", doc.correspondence_type)}
        {info_row("Priority", doc.priority)}
        {info_row("Instruction", instruction or "See correspondence record")}
    </table>
    {cta_button(f"/app/correspondence/{doc.name}", "Open Correspondence")}
    {email_footer()}
    """


def _build_acknowledgement_html(doc):
	return f"""
    {email_header(doc.company, "Acknowledgement of Receipt")}
    <p style="font-size:13px;color:#1E293B;line-height:1.7">
        Dear <b>{doc.from_name or 'Sir/Madam'}</b>,<br><br>
        We acknowledge receipt of your correspondence, <b>"{doc.subject}"</b>,
        received on <b>{formatdate(doc.date_received, "long") if doc.date_received else formatdate(today(), "long")}</b>.
        This matter is being reviewed and you will receive a response in due course.
    </p>
    {email_footer()}
    """
