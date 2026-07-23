# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/hub_api.py
"""
Secretarial Hub Dashboard API
=================================
Composes the per-phase dashboard/list functions already built (AGM, Meeting,
Correspondence, Documents/Legal Register, Executive Support) into three
consolidated views for the secretarial-hub page:

    get_secretary_dashboard(company)
    get_board_dashboard(company)
    get_executive_dashboard(company, executive)

Each section is wrapped in a DocType-existence check so the hub degrades
gracefully (returns what it can, flags what's missing) rather than throwing
if a phase hasn't been deployed to this bench yet.
"""

import frappe
from frappe.utils import getdate, today, date_diff


def _has(doctype):
	return frappe.db.exists("DocType", doctype) is not None


@frappe.whitelist()
def get_secretary_dashboard(company=None):
	result = {"modules_available": {}, "kpis": {}, "upcoming": []}

	if _has("Annual General Meeting"):
		result["modules_available"]["agm"] = True
		from ecclesia.api.agm_api import get_agm_dashboard_stats, get_upcoming_agm_obligations
		result["kpis"]["agm"] = get_agm_dashboard_stats(company)
		result["upcoming"] += [{**o, "source": "AGM"} for o in get_upcoming_agm_obligations(company, 60)]
	else:
		result["modules_available"]["agm"] = False

	if _has("Meeting"):
		result["modules_available"]["meeting"] = True
		from ecclesia.api.meeting_api import get_meeting_dashboard_stats, get_upcoming_meetings
		result["kpis"]["meeting"] = get_meeting_dashboard_stats(company)
		result["upcoming"] += [
			{"source": "Meeting", "title": m["meeting_title"], "due_date": m["meeting_date"],
			 "days_to": m["days_to"], "alert_level": m["alert_level"], "doc_name": m["name"]}
			for m in get_upcoming_meetings(company, 30)
		]
	else:
		result["modules_available"]["meeting"] = False

	if _has("Correspondence"):
		result["modules_available"]["correspondence"] = True
		from ecclesia.api.correspondence_api import get_correspondence_dashboard_stats, get_overdue_correspondence
		result["kpis"]["correspondence"] = get_correspondence_dashboard_stats(company)
		result["upcoming"] += [
			{"source": "Correspondence", "title": c["subject"], "due_date": c.get("due_date") or c.get("response_due_date"),
			 "days_to": c["days_to"], "alert_level": c["alert_level"], "doc_name": c["name"]}
			for c in get_overdue_correspondence(company, 14)
		]
	else:
		result["modules_available"]["correspondence"] = False

	if _has("Legal Register"):
		result["modules_available"]["documents"] = True
		from ecclesia.api.documents_api import get_document_dashboard_stats, get_expiring_items
		result["kpis"]["documents"] = get_document_dashboard_stats(company)
		result["upcoming"] += [
			{"source": e["source"], "title": e["title"], "due_date": str(e["expiry_date"]),
			 "days_to": e["days_to"], "alert_level": e["alert_level"], "doc_name": e["name"]}
			for e in get_expiring_items(company, 60)
		]
	else:
		result["modules_available"]["documents"] = False

	result["upcoming"] = sorted(result["upcoming"], key=lambda x: x.get("days_to", 999))[:25]
	return result


@frappe.whitelist()
def get_board_dashboard(company=None):
	result = {"modules_available": {}, "kpis": {}, "upcoming_board_meetings": [], "pending_signatures": []}

	if _has("Board Resolution"):
		result["modules_available"]["board_resolution"] = True
		filters = {"company": company} if company else {}
		resolutions = frappe.db.get_all(
			"Board Resolution", filters=filters,
			fields=["name", "resolution_title", "meeting_type", "implementation_status",
					"cac_filing_required", "cac_filed"],
		)
		result["kpis"]["resolutions_total"] = len(resolutions)
		result["kpis"]["resolutions_pending_implementation"] = sum(
			1 for r in resolutions if r.implementation_status == "Pending")
		result["kpis"]["cac_filings_outstanding"] = sum(
			1 for r in resolutions if r.cac_filing_required and not r.cac_filed)
		result["kpis"]["written_resolutions"] = sum(
			1 for r in resolutions if r.meeting_type == "Written Resolution")
	else:
		result["modules_available"]["board_resolution"] = False

	if _has("Board Member"):
		result["modules_available"]["board_member"] = True
		members = frappe.db.get_all(
			"Board Member", filters={**({"company": company} if company else {}), "status": "Active"},
			fields=["name", "designation", "is_independent"],
		)
		result["kpis"]["active_board_members"] = len(members)
		result["kpis"]["independent_directors"] = sum(1 for m in members if m.is_independent)
	else:
		result["modules_available"]["board_member"] = False

	if _has("Committee"):
		result["modules_available"]["committee"] = True
		result["kpis"]["active_committees"] = frappe.db.count(
			"Committee", {**({"company": company} if company else {}), "status": "Active"})
	else:
		result["modules_available"]["committee"] = False

	if _has("Meeting"):
		today_date = getdate(today())
		board_meetings = frappe.db.get_all(
			"Meeting",
			filters={**({"company": company} if company else {}), "meeting_category": "Board Meeting",
					 "status": ["not in", ["Cancelled"]]},
			fields=["name", "meeting_title", "meeting_date", "status"],
		)
		for m in board_meetings:
			if not m.meeting_date:
				continue
			days_to = date_diff(getdate(m.meeting_date), today_date)
			if -7 <= days_to <= 60:
				result["upcoming_board_meetings"].append({**m, "days_to": days_to})
		result["upcoming_board_meetings"].sort(key=lambda x: x["days_to"])

	if _has("Board Resolution Signatory"):
		pending = frappe.db.sql(
			"""
			SELECT DISTINCT br.name, br.resolution_title, br.signing_deadline
			FROM `tabBoard Resolution` br
			INNER JOIN `tabBoard Resolution Signatory` s ON s.parent = br.name
			WHERE br.meeting_type = 'Written Resolution' AND br.docstatus = 0 AND s.signed = 0
			""",
			as_dict=True,
		)
		result["pending_signatures"] = pending

	return result


@frappe.whitelist()
def get_executive_dashboard(company=None, executive=None):
	result = {"modules_available": {}}

	if not _has("Executive Appointment"):
		result["modules_available"]["executive_support"] = False
		return result

	result["modules_available"]["executive_support"] = True
	from ecclesia.api.executive_api import (
		get_executive_dashboard_stats, get_todays_appointments,
		get_corporate_calendar, get_upcoming_birthdays, get_upcoming_work_anniversaries,
	)
	result["kpis"] = get_executive_dashboard_stats(company, executive)
	result["todays_appointments"] = get_todays_appointments(executive)
	result["calendar"] = get_corporate_calendar(company, 30)
	result["birthdays"] = get_upcoming_birthdays(company, 14)
	result["anniversaries"] = get_upcoming_work_anniversaries(company, 14)
	return result
