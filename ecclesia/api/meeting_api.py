# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/meeting_api.py
"""
Meeting API — Notifications, Dashboard, Roster Loading
=========================================================
Whitelisted methods:
    get_upcoming_meetings(company, days_ahead)
    get_meeting_dashboard_stats(company)
    load_board_members(meeting_name)
    load_committee_members(meeting_name)
    send_meeting_notice(meeting_name, channel)
    send_meeting_reminder(meeting_name, reminder_type)
    send_minutes_notification(meeting_name)
    send_action_item_alert(meeting_name)
    run_meeting_scheduled_notifications()   ← called by scheduler

Notification triggers:
    1. Meeting Notice        → All invitees (per Meeting Type notice period)
    2. Meeting Reminder      → All notified invitees (24-hour / day-of)
    3. Minutes Ready         → All attendees (after status = Minutes Approved)
    4. Action Item Alert     → Responsible officers (after status = Held)
    5. Overdue Action Alert  → Responsible officers (past due_date, still Open)
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff, cint, flt, now_datetime, formatdate

from ecclesia.utils.email_templates import (
	email_header, email_footer, info_row, status_badge, cta_button, get_officer_email,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_upcoming_meetings(company=None, days_ahead=30):
	"""Return meetings within the next N days, for the Secretary/Board Dashboard."""
	meetings = frappe.db.get_all(
		"Meeting",
		filters={**({"company": company} if company else {}),
				 "status": ["not in", ["Cancelled"]]},
		fields=["name", "meeting_title", "company", "meeting_category", "meeting_date",
				"meeting_time", "status", "notice_compliant", "quorum_met"],
		order_by="meeting_date asc",
		limit=100,
	)
	today_date = getdate(today())
	upcoming = []
	for m in meetings:
		if not m.meeting_date:
			continue
		days_to = date_diff(getdate(m.meeting_date), today_date)
		if -7 <= days_to <= int(days_ahead):
			upcoming.append({
				**m,
				"days_to": days_to,
				"overdue": days_to < 0 and m.status not in ("Held", "Minutes Draft", "Minutes Approved"),
				"alert_level": "red" if (days_to < 0 and m.status not in ("Held", "Minutes Draft", "Minutes Approved"))
							 else "amber" if days_to <= 2
							 else "green",
			})
	return sorted(upcoming, key=lambda x: x["days_to"])


@frappe.whitelist()
def get_meeting_dashboard_stats(company=None):
	"""KPI summary for the Secretary / Board Dashboard."""
	all_meetings = frappe.db.get_all(
		"Meeting",
		filters=({"company": company} if company else {}),
		fields=["name", "meeting_category", "meeting_date", "status",
				"notice_compliant", "quorum_met", "resolutions_passed",
				"resolutions_failed", "open_action_items"],
	)
	today_date = getdate(today())
	current_year = today_date.year

	return {
		"total": len(all_meetings),
		"held_this_year": sum(
			1 for m in all_meetings
			if m.status in ("Held", "Minutes Draft", "Minutes Approved")
			and m.meeting_date and getdate(m.meeting_date).year == current_year
		),
		"board_meetings": sum(1 for m in all_meetings if m.meeting_category == "Board Meeting"),
		"committee_meetings": sum(1 for m in all_meetings if m.meeting_category == "Committee Meeting"),
		"notice_compliant": sum(1 for m in all_meetings if m.notice_compliant),
		"quorum_met": sum(1 for m in all_meetings if m.quorum_met),
		"upcoming_30_days": sum(
			1 for m in all_meetings
			if m.meeting_date and 0 <= date_diff(getdate(m.meeting_date), today_date) <= 30
		),
		"total_resolutions_passed": sum(cint(m.resolutions_passed) for m in all_meetings),
		"open_action_items": sum(cint(m.open_action_items) for m in all_meetings),
	}


# ═══════════════════════════════════════════════════════════════════════════════
#  ROSTER LOADING (whitelisted — callable from JS buttons)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def load_board_members(meeting_name):
	"""Populate the Attendee and Notice Log tables from active Board Members."""
	meeting = frappe.get_doc("Meeting", meeting_name)
	members = frappe.db.get_all(
		"Board Member",
		filters={"company": meeting.company, "status": "Active"},
		fields=["name", "board_member_name", "designation", "email", "phone"],
	)
	if not members:
		frappe.throw(_("No active Board Members found for {0}.").format(meeting.company))

	existing_names = {a.attendee_name for a in (meeting.attendees or [])}
	existing_notice = {n.recipient_name for n in (meeting.notice_logs or [])}
	added = 0

	for m in members:
		if m.board_member_name not in existing_names:
			meeting.append("attendees", {
				"attendee_name": m.board_member_name,
				"attendee_type": "Board Member",
				"designation": m.designation,
				"attendance_status": "Present",
				"email": m.email,
				"phone": m.phone,
			})
			added += 1
		if m.board_member_name not in existing_notice:
			meeting.append("notice_logs", {
				"recipient_type": "Board Member",
				"recipient_name": m.board_member_name,
				"email": m.email,
				"delivery_status": "Pending",
			})

	meeting.total_invitees = len(meeting.notice_logs or [])
	meeting.save(ignore_permissions=True)
	return {"added": added, "total": len(members), "message": f"Loaded {added} board member(s)."}


@frappe.whitelist()
def load_committee_members(meeting_name):
	"""Populate the Attendee and Notice Log tables from the linked Committee's members."""
	meeting = frappe.get_doc("Meeting", meeting_name)
	if not meeting.committee:
		frappe.throw(_("Please set the Committee field before loading committee members."))

	committee = frappe.get_doc("Committee", meeting.committee)
	active_members = [m for m in (committee.members or []) if m.is_active]
	if not active_members:
		frappe.throw(_("No active members found in Committee {0}.").format(meeting.committee))

	existing_names = {a.attendee_name for a in (meeting.attendees or [])}
	existing_notice = {n.recipient_name for n in (meeting.notice_logs or [])}
	added = 0

	for cm in active_members:
		bm = frappe.db.get_value(
			"Board Member", cm.board_member, ["board_member_name", "designation", "email", "phone"], as_dict=True
		)
		if not bm:
			continue
		if bm.board_member_name not in existing_names:
			meeting.append("attendees", {
				"attendee_name": bm.board_member_name,
				"attendee_type": "Committee Member",
				"designation": cm.role or bm.designation,
				"attendance_status": "Present",
				"email": bm.email,
				"phone": bm.phone,
			})
			added += 1
		if bm.board_member_name not in existing_notice:
			meeting.append("notice_logs", {
				"recipient_type": "Committee Member",
				"recipient_name": bm.board_member_name,
				"email": bm.email,
				"delivery_status": "Pending",
			})

	meeting.total_invitees = len(meeting.notice_logs or [])
	meeting.save(ignore_permissions=True)
	return {"added": added, "total": len(active_members), "message": f"Loaded {added} committee member(s)."}


# ═══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATION ENTRY POINTS (whitelisted — callable from JS buttons)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def send_meeting_notice(meeting_name, channel="Email"):
	"""Send the meeting notice + agenda to everyone in the Notice Delivery Log."""
	meeting = frappe.get_doc("Meeting", meeting_name)

	if not meeting.notice_logs:
		frappe.throw(_("No recipients in Notice Delivery Log. Use Load Board/Committee Members first."))

	sent = 0
	failed = 0

	for row in meeting.notice_logs:
		if row.delivery_status in ("Delivered", "Sent"):
			continue
		if not row.email:
			row.delivery_status = "Failed"
			row.remarks = "No email address"
			failed += 1
			continue
		try:
			frappe.sendmail(
				recipients=[row.email],
				subject=f"Notice of {meeting.meeting_category} — {meeting.meeting_title}",
				message=_build_meeting_notice_html(meeting, row.recipient_name),
				reference_doctype="Meeting",
				reference_name=meeting_name,
			)
			row.delivery_status = "Sent"
			row.sent_date = today()
			sent += 1
		except Exception as e:
			row.delivery_status = "Failed"
			row.remarks = str(e)[:200]
			failed += 1

	meeting.members_notified = sent
	if sent > 0 and meeting.status == "Draft":
		meeting.notice_date = today()
		meeting.status = "Notice Sent"
	meeting.save(ignore_permissions=True)

	return {
		"sent": sent, "failed": failed, "total": len(meeting.notice_logs),
		"message": f"✅ {sent} notice(s) sent. ❌ {failed} failed.",
	}


@frappe.whitelist()
def send_meeting_reminder(meeting_name, reminder_type="24_hour"):
	"""reminder_type: '24_hour' | 'day_of'"""
	meeting = frappe.get_doc("Meeting", meeting_name)
	labels = {
		"24_hour": ("24-Hour Reminder", "tomorrow"),
		"day_of": ("Meeting Today", "today"),
	}
	label, when = labels.get(reminder_type, ("Reminder", "soon"))

	recipients = [r.email for r in (meeting.notice_logs or [])
				  if r.email and r.delivery_status in ("Sent", "Delivered")]
	if not recipients:
		return {"sent": 0, "message": "No previously notified attendees found."}

	sent = 0
	for email in recipients:
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"Reminder — {meeting.meeting_title} {label}",
				message=_build_reminder_html(meeting, label, when),
				reference_doctype="Meeting",
				reference_name=meeting_name,
			)
			sent += 1
		except Exception:
			pass

	if reminder_type == "day_of" and meeting.chairperson:
		_notify_chair_and_secretary(meeting)

	frappe.get_doc({
		"doctype": "Comment",
		"comment_type": "Info",
		"reference_doctype": "Meeting",
		"reference_name": meeting_name,
		"content": f"{label} sent to {sent} attendee(s) — {now_datetime()}",
	}).insert(ignore_permissions=True)

	return {"sent": sent, "message": f"Reminder sent to {sent} attendee(s)."}


@frappe.whitelist()
def send_minutes_notification(meeting_name):
	"""Notify all attendees that minutes have been approved."""
	meeting = frappe.get_doc("Meeting", meeting_name)

	if meeting.status != "Minutes Approved":
		frappe.throw(_("Minutes notification can only be sent when status is 'Minutes Approved'."))

	emails = set()
	for row in (meeting.notice_logs or []):
		if row.email and row.delivery_status in ("Sent", "Delivered"):
			emails.add(row.email)
	for a in (meeting.attendees or []):
		if a.email:
			emails.add(a.email)

	for officer in [meeting.chairperson, meeting.meeting_secretary]:
		email = get_officer_email(officer)
		if email:
			emails.add(email)

	emails = {e for e in emails if e}
	if not emails:
		return {"sent": 0, "message": "No recipients found."}

	sent = 0
	for email in emails:
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"Minutes Approved — {meeting.meeting_title}",
				message=_build_minutes_notification_html(meeting),
				reference_doctype="Meeting",
				reference_name=meeting_name,
			)
			sent += 1
		except Exception:
			pass

	return {"sent": sent, "message": f"Minutes notification sent to {sent} recipient(s)."}


@frappe.whitelist()
def send_action_item_alert(meeting_name):
	"""Send each responsible officer their open action item(s) from this meeting."""
	meeting = frappe.get_doc("Meeting", meeting_name)

	open_items = [a for a in (meeting.action_items or [])
				  if a.status in ("Open", "In Progress") and a.responsible]
	if not open_items:
		return {"sent": 0, "message": "No open action items with a responsible officer."}

	by_officer = {}
	for item in open_items:
		by_officer.setdefault(item.responsible, []).append(item)

	sent = 0
	for officer, items in by_officer.items():
		email = get_officer_email(officer)
		if not email:
			continue
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"Action Items Assigned — {meeting.meeting_title}",
				message=_build_action_item_html(meeting, items, officer),
				reference_doctype="Meeting",
				reference_name=meeting_name,
			)
			sent += 1
		except Exception:
			pass

	return {"sent": sent, "message": f"Action item alerts sent to {sent} officer(s)."}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCHEDULER (runs daily via hooks.py scheduler_events)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_meeting_scheduled_notifications():
	"""
	Daily scheduler job — sends time-triggered Meeting notifications automatically.

	Register in hooks.py:
	    scheduler_events = {
	        "daily": [
	            "ecclesia.api.meeting_api.run_meeting_scheduled_notifications"
	        ]
	    }
	"""
	today_date = getdate(today())

	active_meetings = frappe.db.get_all(
		"Meeting",
		filters={"status": ["not in", ["Cancelled"]]},
		fields=["name", "meeting_title", "company", "meeting_date", "status", "notice_date"],
	)

	triggered = []

	for meeting in active_meetings:
		meeting_date = getdate(meeting.meeting_date) if meeting.meeting_date else None
		if not meeting_date:
			continue
		days_to = date_diff(meeting_date, today_date)

		# 24-hour reminder
		if days_to == 1 and meeting.status == "Notice Sent":
			send_meeting_reminder(meeting["name"], "24_hour")
			triggered.append(f"{meeting.name}: 24-hour reminder sent")

		# Day-of alert
		if days_to == 0:
			send_meeting_reminder(meeting["name"], "day_of")
			triggered.append(f"{meeting.name}: day-of alert sent")

		# Overdue meeting still in Draft/Scheduled — internal nudge
		if days_to == -3 and meeting.status not in ("Held", "Minutes Draft", "Minutes Approved"):
			_send_overdue_meeting_alert(meeting["name"], meeting["meeting_title"], meeting["company"])
			triggered.append(f"{meeting.name}: overdue meeting alert")

	# Overdue action items across all meetings (independent of meeting date)
	overdue_items = frappe.db.sql(
		"""
		SELECT parent, responsible, action_description, due_date
		FROM `tabMeeting Action Item`
		WHERE status IN ('Open', 'In Progress') AND due_date < %s
		""",
		(today_date,), as_dict=True,
	)
	if overdue_items:
		_send_overdue_action_alert(overdue_items)
		triggered.append(f"{len(overdue_items)} overdue action item alert(s)")

	frappe.logger().info(f"Meeting Scheduler: {len(triggered)} notification(s) triggered: {triggered}")
	return {"triggered": len(triggered), "details": triggered}


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _notify_chair_and_secretary(meeting):
	for field in ["chairperson", "meeting_secretary"]:
		employee = getattr(meeting, field, None)
		if not employee:
			continue
		email = get_officer_email(employee)
		if not email:
			continue
		name = frappe.db.get_value("Employee", employee, "employee_name") or employee
		frappe.sendmail(
			recipients=[email],
			subject=f"📅 Meeting is TODAY — {meeting.meeting_title}",
			message=_build_day_of_alert_html(meeting, name),
			reference_doctype="Meeting",
			reference_name=meeting.name,
		)


def _send_overdue_meeting_alert(meeting_name, meeting_title, company):
	users = frappe.db.get_all(
		"Has Role",
		filters={"role": ["in", ["System Manager", "Accounts Manager"]]},
		fields=["parent"], distinct=True,
	)
	emails = {frappe.db.get_value("User", u.parent, "email") for u in users}
	emails = {e for e in emails if e and "@" in e}
	if not emails:
		return

	html = f"""
    {email_header(company)}
    <div style="background:#FEF3C7;border-left:5px solid #D97706;padding:16px 20px;
                margin-bottom:24px;border-radius:0 8px 8px 0">
        <div style="font-size:18px;font-weight:700;color:#D97706;margin-bottom:8px">
            ⚠️ Overdue Meeting Not Yet Held
        </div>
        <div style="font-size:14px;color:#1E293B;line-height:1.7">
            <b>{meeting_title}</b> was scheduled for a date that has now passed, and has not
            been marked as Held. Please confirm the meeting status or reschedule.
        </div>
    </div>
    {cta_button(f"/app/meeting/{meeting_name}", "Open Meeting Record")}
    {email_footer()}
    """
	for email in emails:
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"⚠️ Overdue Meeting — {meeting_title}",
				message=html,
				reference_doctype="Meeting",
				reference_name=meeting_name,
			)
		except Exception:
			pass


def _send_overdue_action_alert(overdue_items):
	by_officer = {}
	for item in overdue_items:
		by_officer.setdefault(item.responsible, []).append(item)

	for officer, items in by_officer.items():
		email = get_officer_email(officer)
		if not email:
			continue
		rows = "".join(
			f"""<tr>
				<td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-size:13px">{i.action_description}</td>
				<td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-size:12px;color:#DC2626">
					{formatdate(i.due_date, 'long')}</td>
			</tr>"""
			for i in items
		)
		html = f"""
        {email_header("Overdue Action Items")}
        <p style="font-size:13px;color:#1E293B;line-height:1.7">
            You have <b>{len(items)}</b> overdue action item(s) from Ecclesia meetings:
        </p>
        <table style="width:100%;border-collapse:collapse;border:1px solid #E2E8F0;border-radius:8px;overflow:hidden">
            <thead><tr style="background:#1E3A5F">
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Action</th>
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Was Due</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        {email_footer()}
        """
		try:
			frappe.sendmail(
				recipients=[email],
				subject=f"🚨 {len(items)} Overdue Action Item(s) — Ecclesia",
				message=html,
			)
		except Exception:
			pass


# ═══════════════════════════════════════════════════════════════════════════════
#  HTML EMAIL TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

def _agenda_list(meeting):
	if not meeting.agenda_items:
		return "<p style='color:#64748B;font-size:13px'>Agenda to follow.</p>"
	items = sorted(meeting.agenda_items, key=lambda x: x.item_no or 0)
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


def _build_meeting_notice_html(meeting, recipient_name):
	venue_detail = (
		meeting.venue if meeting.meeting_mode == "Physical"
		else f"{meeting.virtual_platform or 'Online'} — {meeting.virtual_link or 'Link to follow'}"
	)
	mode_icon = "📍" if meeting.meeting_mode == "Physical" else "💻"

	return f"""
    {email_header(meeting.company, f"Notice of {meeting.meeting_category}")}

    <p style="font-size:13px;color:#475569;margin:0 0 20px">Dear <b>{recipient_name}</b>,</p>

    <p style="font-size:14px;color:#1E293B;line-height:1.7;margin:0 0 20px">
        Notice is hereby given of a <b>{meeting.meeting_category}</b> — <b>{meeting.meeting_title}</b> —
        to be held as detailed below.
    </p>

    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
                overflow:hidden;margin-bottom:24px">
        <div style="background:#1E3A5F;padding:12px 16px">
            <span style="color:#93C5FD;font-size:12px;font-weight:700;letter-spacing:1px">MEETING DETAILS</span>
        </div>
        <table style="width:100%;border-collapse:collapse">
            {info_row("📅 Date", formatdate(meeting.meeting_date, "long"), highlight=True)}
            {info_row("🕐 Time", meeting.meeting_time or "To be advised")}
            {info_row(f"{mode_icon} {'Venue' if meeting.meeting_mode=='Physical' else 'Platform'}", venue_detail or "—", highlight=True)}
            {info_row("📋 Category", meeting.meeting_category)}
        </table>
    </div>

    <h3 style="color:#1E3A5F;font-size:15px;margin:0 0 12px;padding-bottom:8px;
               border-bottom:2px solid #3B82F6">Agenda</h3>
    {_agenda_list(meeting)}

    <p style="font-size:13px;color:#475569;margin:24px 0 0;line-height:1.7">
        By Order of the {meeting.meeting_category.replace(' Meeting', '')},<br>
        <b style="color:#1E3A5F">{frappe.db.get_value('Employee', meeting.meeting_secretary, 'employee_name') if meeting.meeting_secretary else 'The Secretary'}</b>
    </p>

    {email_footer()}"""


def _build_reminder_html(meeting, label, when):
	venue_detail = (
		meeting.venue if meeting.meeting_mode == "Physical"
		else f"{meeting.virtual_platform or 'Online'}: {meeting.virtual_link or 'See original notice'}"
	)
	return f"""
    {email_header(meeting.company, f"{meeting.meeting_title} — {label}")}

    <div style="background:linear-gradient(135deg,#FEF3C7,#FDE68A);border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:36px;margin-bottom:8px">⏰</div>
        <h2 style="margin:0;color:#92400E;font-size:18px">Your meeting is {when}!</h2>
        <p style="margin:8px 0 0;color:#78350F;font-size:13px">{meeting.meeting_title}</p>
    </div>

    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden">
        {info_row("📅 Date", formatdate(meeting.meeting_date, "long"), highlight=True)}
        {info_row("🕐 Time", meeting.meeting_time or "See original notice")}
        {info_row("📍 Location", venue_detail or "—")}
    </table>

    {email_footer()}"""


def _build_day_of_alert_html(meeting, officer_name):
	checklist = [
		"Attendance register prepared",
		"Quorum checklist ready",
		"Agenda papers / board pack distributed",
		"Minutes template ready",
		"Recording arranged (if needed)",
	]
	items = "".join(f"<li style='margin:6px 0;font-size:13px;color:#1E293B'>{c}</li>" for c in checklist)
	return f"""
    {email_header(meeting.company, "Meeting Day Checklist")}

    <div style="background:linear-gradient(135deg,#EFF6FF,#DBEAFE);border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:40px;margin-bottom:8px">🏛️</div>
        <h2 style="margin:0;color:#1E40AF;font-size:18px">The meeting is TODAY</h2>
        <p style="margin:8px 0 0;color:#1E3A5F;font-size:13px">Dear <b>{officer_name}</b></p>
    </div>

    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:24px">
        {info_row("📅 Date", formatdate(meeting.meeting_date, "long"), highlight=True)}
        {info_row("🕐 Time", meeting.meeting_time or "—")}
        {info_row("👥 Quorum", f"{meeting.quorum_required or 2} members required")}
    </table>

    <h3 style="color:#1E3A5F;font-size:14px;margin:0 0 10px">📋 Pre-Meeting Checklist</h3>
    <ul style="padding-left:20px;margin:0 0 20px">{items}</ul>

    {cta_button(f"/app/meeting/{meeting.name}", "Open Meeting Record")}
    {email_footer()}"""


def _build_minutes_notification_html(meeting):
	resolutions_html = ""
	if meeting.resolutions:
		passed = [r for r in meeting.resolutions if r.result == "Passed"]
		rows = "".join(
			f"""<tr>
				<td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-size:13px;
						   color:#1E3A5F;font-weight:700">{r.resolution_no}</td>
				<td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-size:13px">{r.resolution_title}</td>
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
                <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Result</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>"""

	return f"""
    {email_header(meeting.company, "Meeting Minutes Approved")}

    <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                padding:20px 24px;margin-bottom:24px;text-align:center">
        <div style="font-size:36px;margin-bottom:8px">📄</div>
        <h2 style="margin:0;color:#1E40AF;font-size:17px">Meeting Minutes Have Been Approved</h2>
    </div>

    <p style="font-size:13px;color:#475569;line-height:1.7;margin:0 0 20px">
        The minutes of <b>{meeting.meeting_title}</b> held on
        <b>{formatdate(meeting.meeting_date, 'long')}</b> have been approved.
    </p>

    {resolutions_html}

    {email_footer()}"""


def _build_action_item_html(meeting, items, officer_id):
	officer_name = frappe.db.get_value("Employee", officer_id, "employee_name") or officer_id
	rows = "".join(
		f"""<tr>
			<td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;font-size:13px">{i.action_description}</td>
			<td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;font-size:12px;color:#64748B">
				{formatdate(i.due_date, 'long') if i.due_date else 'As soon as practicable'}</td>
			<td style="padding:10px 12px;border-bottom:1px solid #E2E8F0;font-size:12px">{i.priority}</td>
		</tr>"""
		for i in items
	)
	return f"""
    {email_header(meeting.company, "Action Items Assigned")}

    <p style="font-size:13px;color:#1E293B;margin:0 0 20px">Dear <b>{officer_name}</b>,</p>

    <p style="font-size:13px;color:#475569;line-height:1.7;margin:0 0 20px">
        The following action item(s) from <b>{meeting.meeting_title}</b>
        (held {formatdate(meeting.meeting_date, 'long')}) have been assigned to you.
    </p>

    <table style="width:100%;border-collapse:collapse;border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;margin-bottom:24px">
        <thead><tr style="background:#1E3A5F">
            <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Action</th>
            <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Due</th>
            <th style="padding:10px 12px;color:white;font-size:12px;text-align:left">Priority</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>

    {cta_button(f"/app/meeting/{meeting.name}", "View Meeting Record")}
    {email_footer()}"""
