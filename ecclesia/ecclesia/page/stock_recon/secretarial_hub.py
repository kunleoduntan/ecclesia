# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/page/secretarial_hub/secretarial_hub.py
"""
Secretarial HQ — Full Secretarial Command Centre (backend)
===============================================================
Mirrors the architecture of compliance_hub.py: whitelisted methods live
here, on the page itself, and compose the domain-level APIs already built
(meeting_api, agm_api, correspondence_api, documents_api, executive_api,
hub_api, ai_assistant_api) rather than re-deriving their logic.

Every domain loader is wrapped in both a DocType-existence check AND a
try/except — the existence check gives a clean "not deployed" signal, the
try/except catches the case where a DocType exists but its real production
schema has diverged from what's assumed here (as already happened once with
Board Resolution in this project). One domain failing must never take the
whole hub down.
"""

import base64
import io
import json

import frappe
from frappe.utils import getdate, today, date_diff, flt, cint, now_datetime


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN SUMMARY (feeds banner, alerts, tab badges, overview cards)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_domain_summary(company=None):
	out = {"modules_available": {}}

	_load_domain(out, "meetings", "Meeting", lambda: _meetings_summary(company))
	_load_domain(out, "agm", "Annual General Meeting", lambda: _agm_summary(company))
	_load_domain(out, "board", "Board Resolution", lambda: _board_summary(company))
	_load_domain(out, "correspondence", "Correspondence", lambda: _correspondence_summary(company))
	_load_domain(out, "documents", "Legal Register", lambda: _documents_summary(company))
	_load_domain(out, "executive", "Executive Appointment", lambda: _executive_summary(company))

	return out


def _load_domain(out, key, doctype_check, loader_fn):
	if not frappe.db.exists("DocType", doctype_check):
		out["modules_available"][key] = False
		out[key] = {}
		return
	try:
		out[key] = loader_fn()
		out["modules_available"][key] = True
	except Exception:
		frappe.log_error(
			title=f"Secretarial Hub: {key} domain load failed",
			message=frappe.get_traceback(),
		)
		out["modules_available"][key] = False
		out[key] = {"_error": True}


def _meetings_summary(company):
	from ecclesia.api.meeting_api import get_meeting_dashboard_stats
	return get_meeting_dashboard_stats(company)


def _agm_summary(company):
	from ecclesia.api.agm_api import get_agm_dashboard_stats
	return get_agm_dashboard_stats(company)


def _board_summary(company):
	from ecclesia.api.hub_api import get_board_dashboard
	board = get_board_dashboard(company)
	kpis = board.get("kpis", {})
	kpis["upcoming_meetings"] = board.get("upcoming_board_meetings", [])
	kpis["pending_signatures"] = board.get("pending_signatures", [])
	return kpis


def _correspondence_summary(company):
	from ecclesia.api.correspondence_api import get_correspondence_dashboard_stats
	return get_correspondence_dashboard_stats(company)


def _documents_summary(company):
	from ecclesia.api.documents_api import get_document_dashboard_stats
	return get_document_dashboard_stats(company)


def _executive_summary(company):
	from ecclesia.api.executive_api import get_executive_dashboard_stats
	return get_executive_dashboard_stats(company)


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORING
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_full_secretarial_score(company=None):
	d = get_domain_summary(company)
	avail = d.get("modules_available", {})
	scores = {}

	if avail.get("meetings"):
		scores["meetings"] = _score_meetings(d["meetings"])
	if avail.get("agm"):
		scores["agm"] = _score_agm(d["agm"])
	if avail.get("board"):
		scores["board"] = _score_board(d["board"])
	if avail.get("correspondence"):
		scores["correspondence"] = _score_correspondence(d["correspondence"])
	if avail.get("documents"):
		scores["documents"] = _score_documents(d["documents"])
	if avail.get("executive"):
		scores["executive"] = _score_executive(d["executive"])

	overall = flt(sum(scores.values()) / len(scores)) if scores else 0

	return {"overall": overall, "domain_scores": scores}


def _clamp(v):
	return max(0, min(100, round(v, 1)))


def _score_meetings(m):
	total = flt(m.get("total"))
	if not total:
		return 100
	notice_rate = flt(m.get("notice_compliant")) / total * 100
	quorum_rate = flt(m.get("quorum_met")) / total * 100
	score = (notice_rate + quorum_rate) / 2
	score -= min(25, flt(m.get("open_action_items")) * 2)
	return _clamp(score)


def _score_agm(a):
	total = flt(a.get("total"))
	if not total:
		return 100
	score = (
		flt(a.get("notice_compliant")) / total * 45
		+ flt(a.get("quorum_met")) / total * 25
		+ flt(a.get("cac_filed")) / total * 30
	)
	score -= min(40, flt(a.get("overdue_agm")) * 15 + flt(a.get("cac_overdue")) * 10)
	return _clamp(score)


def _score_board(b):
	total = flt(b.get("resolutions_total"))
	if not total:
		return 100
	score = 100
	score -= min(45, flt(b.get("cac_filings_outstanding")) * 12)
	score -= min(30, flt(b.get("resolutions_pending_implementation")) / total * 60)
	return _clamp(score)


def _score_correspondence(c):
	total = flt(c.get("total"))
	if not total:
		return 100
	score = 100
	score -= min(55, flt(c.get("overdue_response")) / total * 100)
	score -= min(20, flt(c.get("urgent_open")) * 4)
	return _clamp(score)


def _score_documents(doc):
	total = flt(doc.get("legal_total"))
	if not total:
		return 100
	score = 100
	score -= min(65, flt(doc.get("legal_expired")) / total * 100)
	score -= min(25, flt(doc.get("legal_expiring_soon")) / total * 40)
	return _clamp(score)


def _score_executive(e):
	open_tasks = flt(e.get("open_tasks"))
	if not open_tasks:
		return 100
	overdue = flt(e.get("overdue_tasks"))
	score = 100 - min(85, overdue / open_tasks * 100)
	return _clamp(score)


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB DETAIL LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_meetings_tab(company=None):
	from ecclesia.api.meeting_api import get_meeting_dashboard_stats, get_upcoming_meetings

	filters = {"company": company} if company else {}
	recent = frappe.db.get_all(
		"Meeting", filters={**filters, "docstatus": 1},
		fields=["name", "meeting_title", "meeting_category", "meeting_date", "status",
				"quorum_met", "resolutions_passed", "open_action_items"],
		order_by="meeting_date desc", limit=15,
	)
	by_category = frappe.db.sql(
		"""SELECT meeting_category, COUNT(*) cnt FROM `tabMeeting`
		   WHERE docstatus = 1 %s GROUP BY meeting_category""" % (
			"AND company = %(company)s" if company else ""
		),
		{"company": company}, as_dict=True,
	)
	return {
		"stats": get_meeting_dashboard_stats(company),
		"upcoming": get_upcoming_meetings(company, 30),
		"recent": recent,
		"by_category": by_category,
	}


@frappe.whitelist()
def get_agm_tab(company=None):
	from ecclesia.api.agm_api import get_agm_dashboard_stats, get_upcoming_agm_obligations

	filters = {"company": company} if company else {}
	recent = frappe.db.get_all(
		"Annual General Meeting", filters=filters,
		fields=["name", "agm_title", "agm_type", "agm_date", "status",
				"cac_filed", "notice_compliant", "quorum_met"],
		order_by="agm_date desc", limit=15,
	)
	return {
		"stats": get_agm_dashboard_stats(company),
		"upcoming": get_upcoming_agm_obligations(company, 90),
		"recent": recent,
	}


@frappe.whitelist()
def get_board_tab(company=None):
	from ecclesia.api.hub_api import get_board_dashboard

	board = get_board_dashboard(company)
	filters = {"company": company} if company else {}
	resolutions = frappe.db.get_all(
		"Board Resolution", filters=filters,
		fields=["name", "resolution_title", "meeting_type", "meeting_date",
				"implementation_status", "cac_filing_required", "cac_filed"],
		order_by="meeting_date desc", limit=15,
	)
	members = []
	if frappe.db.exists("DocType", "Board Member"):
		members = frappe.db.get_all(
			"Board Member",
			filters={**filters, "status": "Active"},
			fields=["name", "board_member_name", "designation", "is_independent"],
		)
	return {**board, "resolutions": resolutions, "members": members}


@frappe.whitelist()
def get_correspondence_tab(company=None):
	from ecclesia.api.correspondence_api import get_correspondence_dashboard_stats, get_overdue_correspondence

	filters = {"company": company} if company else {}
	recent = frappe.db.get_all(
		"Correspondence", filters=filters,
		fields=["name", "subject", "correspondence_type", "priority", "status",
				"due_date", "response_status"],
		order_by="modified desc", limit=15,
	)
	by_type = frappe.db.sql(
		"""SELECT correspondence_type, COUNT(*) cnt FROM `tabCorrespondence`
		   WHERE 1=1 %s GROUP BY correspondence_type""" % (
			"AND company = %(company)s" if company else ""
		),
		{"company": company}, as_dict=True,
	)
	return {
		"stats": get_correspondence_dashboard_stats(company),
		"overdue": get_overdue_correspondence(company, 14),
		"recent": recent,
		"by_type": by_type,
	}


@frappe.whitelist()
def get_documents_tab(company=None):
	from ecclesia.api.documents_api import get_document_dashboard_stats, get_expiring_items

	filters = {"company": company} if company else {}
	legal = frappe.db.get_all(
		"Legal Register", filters=filters,
		fields=["name", "instrument_title", "issuing_authority", "expiry_date",
				"status", "compliance_status"],
		order_by="expiry_date asc", limit=15,
	)
	documents = []
	if frappe.db.exists("DocType", "Corporate Document"):
		documents = frappe.db.get_all(
			"Corporate Document", filters=filters,
			fields=["name", "document_title", "document_type", "status", "expiry_date"],
			order_by="modified desc", limit=15,
		)
	seals = []
	if frappe.db.exists("DocType", "Company Seal Register"):
		seals = frappe.db.get_all(
			"Company Seal Register", filters={**filters, "status": "Requested"},
			fields=["name", "seal_request_title", "requested_by", "request_date"],
		)
	return {
		"stats": get_document_dashboard_stats(company),
		"expiring": get_expiring_items(company, 60),
		"legal": legal,
		"documents": documents,
		"pending_seals": seals,
	}


@frappe.whitelist()
def get_executive_tab(company=None):
	from ecclesia.api.executive_api import (
		get_executive_dashboard_stats, get_todays_appointments,
		get_upcoming_birthdays, get_upcoming_work_anniversaries,
	)

	filters = {"company": company} if company else {}
	tasks = frappe.db.get_all(
		"Executive Task", filters={**filters, "status": ["in", ["Open", "In Progress"]]},
		fields=["name", "task_title", "assigned_to", "due_date", "priority", "status"],
		order_by="due_date asc", limit=15,
	)
	return {
		"stats": get_executive_dashboard_stats(company),
		"todays_appointments": get_todays_appointments(),
		"birthdays": get_upcoming_birthdays(company, 14),
		"anniversaries": get_upcoming_work_anniversaries(company, 14),
		"open_tasks": tasks,
	}


# ═══════════════════════════════════════════════════════════════════════════════
#  AI ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_ai_secretarial_analysis(company=None):
	"""
	Sends the full domain summary + score to the AI Assistant seam
	(ai_assistant_api._call_ai) and asks for a structured JSON risk
	assessment, mirroring ComplianceHQ's AI contract: risk_level, summary,
	actions[], strategic_recommendation. Subject to the same limitation as
	the rest of the AI Assistant layer — this will throw a clear error until
	_call_ai() is pointed at your real multi-provider integration.
	"""
	try:
		from ecclesia.api.ai_assistant_api import _call_ai

		domain_data = get_domain_summary(company)
		score_data = get_full_secretarial_score(company)

		prompt = (
			"You are analysing corporate secretarial / governance compliance data for a "
			"Nigerian company. Based on the JSON data below, respond with ONLY a JSON object "
			"(no markdown, no prose outside the JSON) with this exact shape:\n"
			'{"risk_level": "Critical|High|Medium|Low", "summary": "one sentence overview", '
			'"actions": [{"action": "...", "deadline": "...", "authority": "..."}], '
			'"strategic_recommendation": "one paragraph"}\n\n'
			f"DOMAIN SCORES:\n{frappe.as_json(score_data)}\n\n"
			f"DOMAIN DATA:\n{frappe.as_json(domain_data)}"
		)
		response = _call_ai(
			prompt,
			system_prompt="You are a company secretary and governance risk analyst producing a structured JSON risk report.",
			interaction_type="Executive Summary", company=company,
		)
		return {"success": True, "analysis": response}
	except Exception as e:
		return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
#  EXCEL EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def export_secretarial_report(company=None, format="xlsx"):
	try:
		import openpyxl
		from openpyxl.styles import Font, PatternFill, Alignment

		domain = get_domain_summary(company)
		score = get_full_secretarial_score(company)

		wb = openpyxl.Workbook()
		header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
		header_font = Font(bold=True, color="FFFFFF", size=11)
		title_font = Font(bold=True, size=14, color="1E3A5F")

		def style_header(ws, row=1):
			for cell in ws[row]:
				cell.fill = header_fill
				cell.font = header_font
				cell.alignment = Alignment(horizontal="left")

		def autosize(ws):
			for col in ws.columns:
				length = max((len(str(c.value)) if c.value is not None else 0) for c in col)
				ws.column_dimensions[col[0].column_letter].width = min(45, max(12, length + 2))

		# Overview sheet
		ws = wb.active
		ws.title = "Overview"
		ws["A1"] = "Secretarial HQ — Compliance Overview"
		ws["A1"].font = title_font
		ws["A2"] = f"Company: {company or 'All Companies'}"
		ws["A3"] = f"Generated: {now_datetime()}"
		ws["A4"] = f"Overall Score: {score.get('overall', 0)}%"
		ws.append([])
		ws.append(["Domain", "Score (%)"])
		style_header(ws, row=6)
		for k, v in (score.get("domain_scores") or {}).items():
			ws.append([k.title(), v])
		autosize(ws)

		# One sheet per available domain
		sheet_specs = [
			("meetings", "Meetings", ["total", "held_this_year", "board_meetings",
				"committee_meetings", "notice_compliant", "quorum_met", "open_action_items"]),
			("agm", "AGM", ["total", "held_this_year", "cac_filed", "cac_overdue",
				"notice_compliant", "quorum_met", "overdue_agm"]),
			("board", "Board Governance", ["resolutions_total", "resolutions_pending_implementation",
				"cac_filings_outstanding", "active_board_members", "independent_directors", "active_committees"]),
			("correspondence", "Correspondence", ["total", "incoming", "outgoing",
				"pending_response", "overdue_response", "urgent_open"]),
			("documents", "Documents & Legal", ["legal_total", "legal_active",
				"legal_expiring_soon", "legal_expired", "documents_total", "documents_expiring_soon"]),
			("executive", "Executive Support", ["appointments_today", "appointments_this_week",
				"open_tasks", "overdue_tasks", "communications_awaiting_ack"]),
		]
		avail = domain.get("modules_available", {})
		for key, title, fields in sheet_specs:
			if not avail.get(key):
				continue
			ws = wb.create_sheet(title)
			ws.append(["Metric", "Value"])
			style_header(ws)
			data = domain.get(key, {})
			for f in fields:
				ws.append([f.replace("_", " ").title(), data.get(f, "—")])
			autosize(ws)

		buf = io.BytesIO()
		wb.save(buf)
		buf.seek(0)
		file_data = base64.b64encode(buf.read()).decode("utf-8")
		file_name = f"Secretarial_HQ_Report_{company or 'All'}_{getdate(today())}.xlsx".replace(" ", "_")

		return {"success": True, "file_data": file_data, "file_name": file_name}
	except Exception as e:
		frappe.log_error(title="Secretarial Hub: Excel export failed", message=frappe.get_traceback())
		return {"success": False, "error": str(e)}
