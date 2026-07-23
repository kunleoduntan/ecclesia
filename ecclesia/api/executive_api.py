# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/executive_api.py
"""
Executive Support API
=========================
Whitelisted methods:
    load_recipients(communication_name)
    dispatch_communication(communication_name)
    acknowledge_communication(communication_name, employee)
    send_acknowledgement_reminder(communication_name)
    get_executive_dashboard_stats(company, executive)
    get_todays_appointments(executive)
    get_upcoming_birthdays(company, days_ahead)
    get_upcoming_work_anniversaries(company, days_ahead)
    get_corporate_calendar(company, days_ahead)
    run_executive_scheduled_notifications()   ← called by scheduler

Notes on scope: birthday/anniversary helpers read Employee.date_of_birth and
Employee.date_of_joining directly — standard core HR fields, not new DocTypes,
per the existing Ecclesia convention of reusing Employee rather than
duplicating personnel data.
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff, formatdate, now_datetime

from ecclesia.utils.email_templates import email_header, email_footer, info_row, cta_button, get_officer_email


# ═══════════════════════════════════════════════════════════════════════════════
#  RECIPIENT LOADING & DISPATCH
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def load_recipients(communication_name):
	"""Populate the Recipients table based on audience_type."""
	doc = frappe.get_doc("Executive Communication", communication_name)

	filters = {"company": doc.company, "status": "Active"}
	if doc.audience_type == "Department" and doc.department:
		filters["department"] = doc.department
	elif doc.audience_type == "Management Team":
		# Best-effort: employees whose designation contains a common management keyword.
		# Flagging this as a heuristic rather than a hard rule since "Management Team"
		# isn't a structural field on Employee in core ERPNext.
		filters["designation"] = ["like", "%Manager%"]

	if doc.audience_type == "Specific Employees":
		return {"added": 0, "message": "Audience is 'Specific Employees' — add rows to Recipients manually."}

	employees = frappe.db.get_all("Employee", filters=filters, fields=["name"])
	if not employees:
		frappe.throw(_("No active employees found matching the selected audience."))

	existing = {r.employee for r in (doc.recipients or [])}
	added = 0
	for emp in employees:
		if emp.name not in existing:
			doc.append("recipients", {"employee": emp.name})
			added += 1

	doc.save(ignore_permissions=True)
	return {"added": added, "message": f"Loaded {added} recipient(s)."}


@frappe.whitelist()
def dispatch_communication(communication_name):
	"""Email the message to every recipient. Requires the doc to be submitted."""
	doc = frappe.get_doc("Executive Communication", communication_name)
	if doc.docstatus != 1:
		frappe.throw(_("Submit this communication before dispatching."))
	if not doc.recipients:
		frappe.throw(_("No recipients to dispatch to."))

	sent = 0
	failed = 0
	for row in doc.recipients:
		if row.sent_date:
			continue
		email = get_officer_email(row.employee)
		if not email:
			failed += 1
			continue
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"{doc.communication_type}: {doc.subject}",
				message=_build_communication_html(doc),
				reference_doctype="Executive Communication",
				reference_name=communication_name,
			)
			row.sent_date = today()
			sent += 1
		except Exception:
			failed += 1

	doc.save(ignore_permissions=True)
	return {"sent": sent, "failed": failed, "message": f"✅ {sent} sent, ❌ {failed} failed."}


@frappe.whitelist()
def acknowledge_communication(communication_name, employee):
	"""Called by a recipient (or on their behalf) to record acknowledgement."""
	doc = frappe.get_doc("Executive Communication", communication_name)
	row = next((r for r in (doc.recipients or []) if r.employee == employee), None)
	if not row:
		frappe.throw(_("{0} is not a recipient of this communication.").format(employee))
	row.acknowledged = 1
	row.acknowledged_date = today()
	if not row.read_date:
		row.read_date = today()
	doc.save(ignore_permissions=True)
	return {"message": "Acknowledgement recorded."}


@frappe.whitelist()
def send_acknowledgement_reminder(communication_name):
	doc = frappe.get_doc("Executive Communication", communication_name)
	outstanding = [r for r in (doc.recipients or []) if not r.acknowledged]
	if not outstanding:
		return {"sent": 0, "message": "All recipients have already acknowledged."}

	sent = 0
	for row in outstanding:
		email = get_officer_email(row.employee)
		if not email:
			continue
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"Reminder — Acknowledgement Required: {doc.subject}",
				message=_build_reminder_html(doc),
				reference_doctype="Executive Communication",
				reference_name=communication_name,
			)
			sent += 1
		except Exception:
			pass
	return {"sent": sent, "message": f"Reminder sent to {sent} outstanding recipient(s)."}


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_executive_dashboard_stats(company=None, executive=None):
	appt_filters = {**({"company": company} if company else {}), **({"executive": executive} if executive else {})}
	appointments = frappe.db.get_all("Executive Appointment", filters=appt_filters,
		fields=["name", "appointment_date", "status"])

	task_filters = {**({"company": company} if company else {})}
	tasks = frappe.db.get_all("Executive Task", filters=task_filters,
		fields=["name", "status", "due_date", "escalated"])

	comm_filters = {**({"company": company} if company else {})}
	comms = frappe.db.get_all("Executive Communication", filters=comm_filters,
		fields=["name", "status", "requires_acknowledgement", "total_recipients", "total_acknowledged"])

	today_date = getdate(today())

	return {
		"appointments_today": sum(1 for a in appointments if a.appointment_date and getdate(a.appointment_date) == today_date
								   and a.status not in ("Cancelled",)),
		"appointments_this_week": sum(1 for a in appointments if a.appointment_date
									   and 0 <= date_diff(getdate(a.appointment_date), today_date) <= 7
									   and a.status not in ("Cancelled",)),
		"open_tasks": sum(1 for t in tasks if t.status in ("Open", "In Progress")),
		"overdue_tasks": sum(1 for t in tasks if t.status in ("Open", "In Progress") and t.due_date
							  and getdate(t.due_date) < today_date),
		"escalated_tasks": sum(1 for t in tasks if t.escalated and t.status not in ("Completed", "Cancelled")),
		"pending_communications": sum(1 for c in comms if c.status == "Draft"),
		"communications_awaiting_ack": sum(
			1 for c in comms
			if c.requires_acknowledgement and c.status == "Sent"
			and (c.total_acknowledged or 0) < (c.total_recipients or 0)
		),
	}


@frappe.whitelist()
def get_todays_appointments(executive=None):
	filters = {"appointment_date": today(), "status": ["not in", ["Cancelled"]]}
	if executive:
		filters["executive"] = executive
	return frappe.db.get_all(
		"Executive Appointment", filters=filters,
		fields=["name", "appointment_title", "start_time", "end_time", "appointment_type",
				"meeting_with", "location", "priority"],
		order_by="start_time asc",
	)


@frappe.whitelist()
def get_upcoming_birthdays(company=None, days_ahead=14):
	"""Reads Employee.date_of_birth directly — no separate DocType needed."""
	filters = {"status": "Active"}
	if company:
		filters["company"] = company
	employees = frappe.db.get_all("Employee", filters=filters,
		fields=["name", "employee_name", "date_of_birth", "designation"])

	today_date = getdate(today())
	upcoming = []
	for e in employees:
		if not e.date_of_birth:
			continue
		dob = getdate(e.date_of_birth)
		next_bday = dob.replace(year=today_date.year)
		if next_bday < today_date:
			next_bday = dob.replace(year=today_date.year + 1)
		days_to = date_diff(next_bday, today_date)
		if 0 <= days_to <= int(days_ahead):
			upcoming.append({**e, "days_to": days_to, "next_birthday": str(next_bday)})

	return sorted(upcoming, key=lambda x: x["days_to"])


@frappe.whitelist()
def get_upcoming_work_anniversaries(company=None, days_ahead=14):
	"""Reads Employee.date_of_joining directly — no separate DocType needed."""
	filters = {"status": "Active"}
	if company:
		filters["company"] = company
	employees = frappe.db.get_all("Employee", filters=filters,
		fields=["name", "employee_name", "date_of_joining", "designation"])

	today_date = getdate(today())
	upcoming = []
	for e in employees:
		if not e.date_of_joining:
			continue
		doj = getdate(e.date_of_joining)
		next_anniv = doj.replace(year=today_date.year)
		if next_anniv < today_date:
			next_anniv = doj.replace(year=today_date.year + 1)
		days_to = date_diff(next_anniv, today_date)
		if 0 <= days_to <= int(days_ahead):
			years = next_anniv.year - doj.year
			upcoming.append({**e, "days_to": days_to, "next_anniversary": str(next_anniv), "years": years})

	return sorted(upcoming, key=lambda x: x["days_to"])


@frappe.whitelist()
def get_corporate_calendar(company=None, days_ahead=30):
	"""
	Aggregates dates across the Secretarial module into one feed for the
	Corporate Calendar dashboard widget: executive appointments, meetings,
	legal register expiries, birthdays, and anniversaries.
	"""
	today_date = getdate(today())
	events = []

	appts = frappe.db.get_all(
		"Executive Appointment",
		filters={**({"company": company} if company else {}), "status": ["not in", ["Cancelled"]]},
		fields=["name", "appointment_title", "appointment_date"],
	)
	for a in appts:
		if a.appointment_date and 0 <= date_diff(getdate(a.appointment_date), today_date) <= int(days_ahead):
			events.append({"type": "Appointment", "title": a.appointment_title, "date": str(a.appointment_date), "ref": a.name})

	if frappe.db.exists("DocType", "Meeting"):
		meetings = frappe.db.get_all(
			"Meeting",
			filters={**({"company": company} if company else {}), "status": ["not in", ["Cancelled"]]},
			fields=["name", "meeting_title", "meeting_date"],
		)
		for m in meetings:
			if m.meeting_date and 0 <= date_diff(getdate(m.meeting_date), today_date) <= int(days_ahead):
				events.append({"type": "Meeting", "title": m.meeting_title, "date": str(m.meeting_date), "ref": m.name})

	if frappe.db.exists("DocType", "Legal Register"):
		legal = frappe.db.get_all(
			"Legal Register",
			filters={**({"company": company} if company else {}), "status": ["not in", ["Renewed"]]},
			fields=["name", "instrument_title", "expiry_date"],
		)
		for l in legal:
			if l.expiry_date and 0 <= date_diff(getdate(l.expiry_date), today_date) <= int(days_ahead):
				events.append({"type": "Legal Expiry", "title": l.instrument_title, "date": str(l.expiry_date), "ref": l.name})

	for b in get_upcoming_birthdays(company, days_ahead):
		events.append({"type": "Birthday", "title": f"{b['employee_name']}'s Birthday", "date": b["next_birthday"], "ref": b["name"]})

	for a in get_upcoming_work_anniversaries(company, days_ahead):
		events.append({"type": "Work Anniversary", "title": f"{a['employee_name']} — {a['years']} Year(s)", "date": a["next_anniversary"], "ref": a["name"]})

	return sorted(events, key=lambda x: x["date"])


# ═══════════════════════════════════════════════════════════════════════════════
#  SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_executive_scheduled_notifications():
	"""
	Daily scheduler job.

	Register in hooks.py:
	    scheduler_events = {
	        "daily": [
	            "ecclesia.api.executive_api.run_executive_scheduled_notifications"
	        ]
	    }
	"""
	today_date = getdate(today())
	triggered = []

	# Tomorrow's appointment digest, per executive
	tomorrow_appts = frappe.db.sql(
		"""
		SELECT executive, COUNT(*) as cnt
		FROM `tabExecutive Appointment`
		WHERE appointment_date = %s AND status NOT IN ('Cancelled')
		GROUP BY executive
		""",
		(frappe.utils.add_days(today_date, 1),), as_dict=True,
	)
	for row in tomorrow_appts:
		email = get_officer_email(row.executive)
		if not email:
			continue
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"📅 {row.cnt} appointment(s) tomorrow",
				message=f"{email_header('Tomorrow')}<p style='font-size:13px'>You have <b>{row.cnt}</b> appointment(s) scheduled tomorrow.</p>{email_footer()}",
			)
			triggered.append(f"appointment digest sent to {row.executive}")
		except Exception:
			pass

	# Overdue Executive Tasks — escalate after 3 days overdue if not already escalated
	overdue_tasks = frappe.db.get_all(
		"Executive Task",
		filters={"status": ["in", ["Open", "In Progress"]], "escalated": 0},
		fields=["name", "task_title", "due_date", "assigned_to", "assigned_by"],
	)
	for t in overdue_tasks:
		if not t.due_date:
			continue
		days_overdue = date_diff(today_date, getdate(t.due_date))
		if days_overdue >= 3:
			frappe.db.set_value("Executive Task", t.name, {
				"escalated": 1,
				"escalated_to": t.assigned_by,
				"escalated_date": today_date,
			})
			email = get_officer_email(t.assigned_by)
			if email:
				try:
					frappe.sendmail(
						recipients=[email],
						subject=f"🚨 Task Escalated (Overdue): {t.task_title}",
						message=f"{email_header('Task Escalation')}<p style='font-size:13px'>"
								f"<b>{t.task_title}</b> is {days_overdue} day(s) overdue and has been escalated to you.</p>{email_footer()}",
					)
				except Exception:
					pass
			triggered.append(f"{t.name}: escalated")

	# Acknowledgement deadline reminders
	comms = frappe.db.get_all(
		"Executive Communication",
		filters={"requires_acknowledgement": 1, "status": "Sent"},
		fields=["name", "acknowledgement_deadline", "total_recipients", "total_acknowledged"],
	)
	for c in comms:
		if not c.acknowledgement_deadline:
			continue
		days_to = date_diff(getdate(c.acknowledgement_deadline), today_date)
		if days_to in (1, 0) and (c.total_acknowledged or 0) < (c.total_recipients or 0):
			send_acknowledgement_reminder(c.name)
			triggered.append(f"{c.name}: acknowledgement reminder")

	frappe.logger().info(f"Executive Scheduler: {len(triggered)} notification(s) triggered: {triggered}")
	return {"triggered": len(triggered), "details": triggered}


# ═══════════════════════════════════════════════════════════════════════════════
#  HTML TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

def _build_communication_html(doc):
	return f"""
    {email_header(doc.company, doc.communication_type)}
    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:20px">
        {info_row("From", frappe.db.get_value('Employee', doc.issued_by, 'employee_name') or doc.issued_by, highlight=True)}
        {info_row("Date", formatdate(doc.issue_date, "long"))}
        {info_row("Priority", doc.priority)}
    </table>
    <div style="font-size:14px;color:#1E293B;line-height:1.7">{doc.message_body}</div>
    {f"<p style='margin-top:20px;font-size:12px;color:#DC2626'><b>Acknowledgement required by {formatdate(doc.acknowledgement_deadline, 'long')}.</b></p>" if doc.requires_acknowledgement and doc.acknowledgement_deadline else ""}
    {email_footer()}
    """


def _build_reminder_html(doc):
	return f"""
    {email_header(doc.company, "Acknowledgement Reminder")}
    <p style="font-size:13px;color:#1E293B;line-height:1.7">
        Please acknowledge receipt of <b>{doc.subject}</b>
        {f"by <b>{formatdate(doc.acknowledgement_deadline, 'long')}</b>" if doc.acknowledgement_deadline else ""}.
    </p>
    {cta_button(f"/app/executive-communication/{doc.name}", "Open Communication")}
    {email_footer()}
    """
