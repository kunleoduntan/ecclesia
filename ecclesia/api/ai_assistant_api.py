# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/ai_assistant_api.py
"""
Ecclesia AI Assistant
========================
Whitelisted methods:
    summarize_meeting_minutes(meeting_name)
    generate_draft_minutes(meeting_name)
    suggest_agenda_from_history(company, meeting_category, committee=None)
    draft_correspondence_response(correspondence_name, instructions=None)
    generate_executive_summary(company, period_days=30)
    analyze_attendance_trends(company, meeting_category=None, lookback=6)
    identify_overdue_action_items(company)

── IMPORTANT ──────────────────────────────────────────────────────────────
Every function here routes through _call_ai() at the bottom of this file.
That function does NOT know the real shape of your existing multi-provider
AI integration (OpenAI/DeepSeek/Anthropic/Gemini) — I've never seen that
script. It tries a couple of plausible import paths and raises a clear
frappe.throw() if none resolve, rather than silently guessing at a request/
response shape that might send malformed calls or eat API costs on a
misconfigured integration. Once you share the real module, replace the body
of _call_ai() with a direct call to it — nothing else in this file needs
to change, since every function below already treats _call_ai() as a plain
(prompt, system_prompt) -> str function.

Every call is now logged to the "AI Interaction Log" DocType — prompt,
response, success/failure, and (where relevant) which record it was called
against — so AI-generated content in a governance system stays auditable.
─────────────────────────────────────────────────────────────────────────
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff, add_days, flt


# ═══════════════════════════════════════════════════════════════════════════════
#  MEETING MINUTES
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def summarize_meeting_minutes(meeting_name):
	"""Condense the Minutes/Resolutions/Action Items of a Meeting into an
	executive-readable summary, saved to the ai_insights field."""
	doc = frappe.get_doc("Meeting", meeting_name)

	minutes_text = "\n".join(
		f"- {m.topic or ''}: {m.discussion_summary or ''} → {m.decision or ''}"
		for m in (doc.minutes or [])
	)
	resolutions_text = "\n".join(
		f"- Res #{r.resolution_no} ({r.result}): {r.resolution_title}"
		for r in (doc.resolutions or [])
	)
	actions_text = "\n".join(
		f"- {a.action_description} (Owner: {a.responsible}, Due: {a.due_date}, Status: {a.status})"
		for a in (doc.action_items or [])
	)

	prompt = (
		f"Summarize the following board/committee meeting into a concise executive briefing "
		f"(max 200 words), covering: key decisions, resolutions passed, and outstanding actions.\n\n"
		f"Meeting: {doc.meeting_title}\nDate: {doc.meeting_date}\n\n"
		f"MINUTES:\n{minutes_text or 'None recorded.'}\n\n"
		f"RESOLUTIONS:\n{resolutions_text or 'None recorded.'}\n\n"
		f"ACTION ITEMS:\n{actions_text or 'None recorded.'}"
	)

	summary = _call_ai(
		prompt, system_prompt="You are a corporate secretary drafting an executive briefing.",
		interaction_type="Meeting Minutes Summary", reference_doctype="Meeting",
		reference_document=meeting_name, company=doc.company,
	)
	doc.db_set("ai_insights", summary)
	return {"summary": summary}


@frappe.whitelist()
def generate_draft_minutes(meeting_name):
	"""Draft minutes text per agenda item, from the agenda + any free-text notes
	already on the meeting, to give the secretary a starting point rather than
	a blank page. Does NOT overwrite existing minutes rows."""
	doc = frappe.get_doc("Meeting", meeting_name)
	if not doc.agenda_items:
		frappe.throw(_("No agenda items to draft minutes from."))

	existing_topics = {m.topic for m in (doc.minutes or [])}
	agenda_text = "\n".join(f"{a.item_no}. {a.agenda_title} ({a.agenda_type})" for a in doc.agenda_items)

	prompt = (
		f"For each agenda item below, write one short draft minute (1-2 sentences) describing "
		f"what would typically be discussed and decided, formatted as:\n"
		f"ITEM_NO | TOPIC | DRAFT_DISCUSSION | DRAFT_DECISION\n\n"
		f"Meeting: {doc.meeting_title} ({doc.meeting_category})\nAgenda:\n{agenda_text}"
	)
	raw = _call_ai(
		prompt, system_prompt="You are a corporate secretary drafting placeholder minutes for a secretary to review and edit.",
		interaction_type="Draft Minutes", reference_doctype="Meeting",
		reference_document=meeting_name, company=doc.company,
	)

	added = 0
	for line in raw.splitlines():
		parts = [p.strip() for p in line.split("|")]
		if len(parts) != 4:
			continue
		_, topic, discussion, decision = parts
		if topic in existing_topics:
			continue
		doc.append("minutes", {
			"topic": topic,
			"discussion_summary": discussion,
			"decision": decision,
		})
		added += 1

	if added:
		doc.save(ignore_permissions=True)
	return {"added": added, "message": f"Drafted {added} minute entry(ies) — please review before approving."}


# ═══════════════════════════════════════════════════════════════════════════════
#  AGENDA SUGGESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def suggest_agenda_from_history(company, meeting_category="Board Meeting", committee=None):
	"""Look at the last 3 meetings of the same category (and committee, if given)
	and suggest recurring standing items plus carried-over open action items."""
	filters = {"company": company, "meeting_category": meeting_category, "docstatus": 1}
	if committee:
		filters["committee"] = committee

	past_meetings = frappe.db.get_all(
		"Meeting", filters=filters, fields=["name"], order_by="meeting_date desc", limit=3
	)
	if not past_meetings:
		return {"suggested_items": [], "message": "No past meetings found to base suggestions on."}

	agenda_titles = []
	open_actions = []
	for pm in past_meetings:
		doc = frappe.get_doc("Meeting", pm.name)
		agenda_titles += [a.agenda_title for a in (doc.agenda_items or [])]
		open_actions += [
			a.action_description for a in (doc.action_items or [])
			if a.status in ("Open", "In Progress")
		]

	prompt = (
		f"Based on the agenda items from the last {len(past_meetings)} {meeting_category}(s) below, "
		f"suggest a standing agenda for the next meeting. List recurring/standard items first, "
		f"then note any carried-over open items that should be revisited. One item per line.\n\n"
		f"PAST AGENDA ITEMS:\n{chr(10).join('- ' + t for t in agenda_titles)}\n\n"
		f"OPEN ACTIONS TO REVISIT:\n{chr(10).join('- ' + a for a in open_actions) or 'None'}"
	)
	suggestion = _call_ai(
		prompt, system_prompt="You are a corporate secretary preparing a meeting agenda.",
		interaction_type="Agenda Suggestion", company=company,
	)
	return {"suggested_items": suggestion.splitlines(), "based_on": [m.name for m in past_meetings]}


# ═══════════════════════════════════════════════════════════════════════════════
#  CORRESPONDENCE DRAFTING
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def draft_correspondence_response(correspondence_name, instructions=None):
	"""Draft a reply body for a piece of correspondence, saved to response_summary
	for the secretary to review — never auto-sent."""
	doc = frappe.get_doc("Correspondence", correspondence_name)

	prompt = (
		f"Draft a professional reply to the correspondence below. "
		f"{f'Specific instructions: {instructions}' if instructions else 'Keep it courteous, concise, and clear about next steps.'}\n\n"
		f"Original Subject: {doc.subject}\n"
		f"From: {doc.from_name or doc.to_name or 'N/A'}\n"
		f"Summary: {doc.body_summary or '(no summary recorded)'}"
	)
	draft = _call_ai(
		prompt, system_prompt="You are a company secretary drafting correspondence on behalf of the organisation.",
		interaction_type="Correspondence Draft", reference_doctype="Correspondence",
		reference_document=correspondence_name, company=doc.company,
	)
	doc.db_set("response_summary", draft)
	return {"draft": draft, "message": "Draft saved to Response Summary — please review before sending."}


# ═══════════════════════════════════════════════════════════════════════════════
#  EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_executive_summary(company=None, period_days=30):
	"""Pull KPIs across every deployed phase and produce a narrative summary
	for the CEO/Board — the AI-flavoured version of the Secretary Dashboard."""
	from ecclesia.api.hub_api import get_secretary_dashboard, get_board_dashboard

	secretary_data = get_secretary_dashboard(company)
	board_data = get_board_dashboard(company)

	upcoming_lines = [
		f"- {u.get('title', '')}" for u in secretary_data.get("upcoming", [])[:10]
	]
	prompt = (
		f"Write a {period_days}-day corporate governance executive summary (max 250 words) for the CEO, "
		f"based on the following data. Highlight risks (overdue items, compliance gaps) first, "
		f"then routine activity.\n\n"
		f"SECRETARY DASHBOARD DATA:\n{frappe.as_json(secretary_data.get('kpis', {}))}\n\n"
		f"BOARD DASHBOARD DATA:\n{frappe.as_json(board_data.get('kpis', {}))}\n\n"
		f"UPCOMING/OVERDUE ITEMS ({len(secretary_data.get('upcoming', []))} total):\n"
		+ "\n".join(upcoming_lines)
	)
	summary = _call_ai(
		prompt, system_prompt="You are a company secretary briefing the CEO on corporate governance status.",
		interaction_type="Executive Summary", company=company,
	)
	return {"summary": summary}


# ═══════════════════════════════════════════════════════════════════════════════
#  ATTENDANCE TRENDS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def analyze_attendance_trends(company=None, meeting_category=None, lookback=6):
	"""Compute attendance rates over the last N meetings and ask the AI for
	a short commentary — data is computed in Python (reliable), only the
	narrative wrapper is AI-generated."""
	filters = {**({"company": company} if company else {}),
			   **({"meeting_category": meeting_category} if meeting_category else {}),
			   "docstatus": 1}
	meetings = frappe.db.get_all(
		"Meeting", filters=filters,
		fields=["name", "meeting_title", "meeting_date", "total_invitees", "total_attendees", "quorum_met"],
		order_by="meeting_date desc", limit=int(lookback),
	)
	if not meetings:
		return {"trend": [], "commentary": "No meeting data available for analysis."}

	trend = []
	for m in meetings:
		rate = (flt(m.total_attendees) / flt(m.total_invitees) * 100) if m.total_invitees else 0
		trend.append({
			"meeting": m.meeting_title, "date": str(m.meeting_date),
			"attendance_rate": round(rate, 1), "quorum_met": bool(m.quorum_met),
		})

	trend_lines = [
		f"- {t['meeting']} ({t['date']}): {t['attendance_rate']}% attendance, quorum met: {t['quorum_met']}"
		for t in trend
	]
	prompt = (
		f"Here is attendance data for the last {len(trend)} meetings (most recent first):\n"
		+ "\n".join(trend_lines) +
		"\n\nIn 2-3 sentences, comment on the trend (improving/declining/stable) and flag any quorum risk."
	)
	commentary = _call_ai(
		prompt, system_prompt="You are a corporate secretary analyzing board governance metrics.",
		interaction_type="Attendance Analysis", company=company,
	)
	return {"trend": trend, "commentary": commentary}


# ═══════════════════════════════════════════════════════════════════════════════
#  OVERDUE ACTION DIGEST
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def identify_overdue_action_items(company=None):
	"""Data-driven (not AI-guessed) list of overdue action items across Meeting
	and Executive Task, with an AI-written one-paragraph priority narrative."""
	today_date = getdate(today())
	overdue = []

	if frappe.db.exists("DocType", "Meeting"):
		rows = frappe.db.sql(
			"""
			SELECT mai.parent, mai.action_description, mai.responsible, mai.due_date, m.company
			FROM `tabMeeting Action Item` mai
			INNER JOIN `tabMeeting` m ON m.name = mai.parent
			WHERE mai.status IN ('Open', 'In Progress') AND mai.due_date < %s
			""" + (" AND m.company = %s" if company else ""),
			(today_date, company) if company else (today_date,), as_dict=True,
		)
		overdue += [{"source": "Meeting", **r} for r in rows]

	if frappe.db.exists("DocType", "Executive Task"):
		filters = {"status": ["in", ["Open", "In Progress"]], "due_date": ["<", today_date]}
		if company:
			filters["company"] = company
		rows = frappe.db.get_all("Executive Task", filters=filters,
			fields=["name as parent", "task_title as action_description", "assigned_to as responsible", "due_date", "company"])
		overdue += [{"source": "Executive Task", **r} for r in rows]

	if not overdue:
		return {"overdue": [], "commentary": "No overdue action items — clean sheet."}

	prompt = (
		f"There are {len(overdue)} overdue action items across the organisation's meetings and "
		f"executive tasks. In one short paragraph, summarize the risk and suggest which 2-3 should "
		f"be prioritized first, based on this list:\n\n"
		+ "\n".join(f"- {o['action_description']} (owner: {o['responsible']}, was due {o['due_date']})" for o in overdue[:20])
	)
	commentary = _call_ai(
		prompt, system_prompt="You are a company secretary triaging overdue governance action items.",
		interaction_type="Overdue Action Digest", company=company,
	)
	return {"overdue": overdue, "commentary": commentary}


# ═══════════════════════════════════════════════════════════════════════════════
#  AI PROVIDER SEAM + LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def _call_ai(prompt, system_prompt=None, interaction_type="Other",
			 reference_doctype=None, reference_document=None, company=None):
	"""
	Single seam every function above routes through. Tries a couple of
	plausible import paths for your existing multi-provider AI integration;
	raises a clear, actionable error if none resolve rather than silently
	returning garbage or guessing at a request format.

	Every call — success or failure — is logged to "AI Interaction Log" for
	auditability, since this is a governance system and AI-generated content
	(minutes, correspondence drafts, executive summaries) needs a paper trail.
	"""
	candidate_paths = [
		"ecclesia.utils.ai_provider.get_ai_completion",
		"ecclesia.ai.get_ai_completion",
		"ecclesia.utils.ai.get_completion",
	]

	response_text = None
	error_text = None

	for path in candidate_paths:
		module_path, func_name = path.rsplit(".", 1)
		try:
			module = frappe.get_module(module_path)
			func = getattr(module, func_name, None)
			if func:
				response_text = func(prompt, system_prompt=system_prompt)
				break
		except ImportError:
			continue
		except Exception as e:
			error_text = str(e)
			break

	if response_text is None and not error_text:
		error_text = (
			f"No AI provider integration found at any of: {', '.join(candidate_paths)}. "
			f"Point _call_ai() in ai_assistant_api.py at your existing multi-provider AI script."
		)

	_log_interaction(
		prompt=prompt, response=response_text, error=error_text,
		interaction_type=interaction_type, reference_doctype=reference_doctype,
		reference_document=reference_document, company=company,
	)

	if response_text is None:
		frappe.throw(_(error_text))

	return response_text


def _log_interaction(prompt, response, error, interaction_type, reference_doctype, reference_document, company):
	try:
		log = frappe.new_doc("AI Interaction Log")
		log.interaction_type = interaction_type or "Other"
		log.status = "Failed" if error else "Success"
		log.company = company
		log.reference_doctype = reference_doctype
		log.reference_document = reference_document
		log.prompt = prompt
		log.response = response
		log.error_message = (error or "")[:500]
		log.insert(ignore_permissions=True)
	except Exception:
		# Logging must never be the reason an AI call fails outright.
		frappe.log_error(title="AI Interaction Log write failed", message=frappe.get_traceback())
