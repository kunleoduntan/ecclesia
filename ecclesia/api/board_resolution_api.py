# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/board_resolution_api.py
"""
Board Resolution API — Signatory Roster & Circulation Notifications
=======================================================================
Whitelisted methods:
    load_signatories(resolution_name)
    send_circulation_notice(resolution_name)
    send_signing_reminder(resolution_name)
"""

import frappe
from frappe import _
from frappe.utils import today, formatdate

from ecclesia.utils.email_templates import email_header, email_footer, info_row, cta_button


@frappe.whitelist()
def load_signatories(resolution_name):
	"""Populate the Signatories table from active Board Members of the resolution's company."""
	doc = frappe.get_doc("Board Resolution", resolution_name)
	members = frappe.db.get_all(
		"Board Member",
		filters={"company": doc.company, "status": "Active"},
		fields=["name", "board_member_name"],
	)
	if not members:
		frappe.throw(_("No active Board Members found for {0}.").format(doc.company))

	existing = {s.board_member for s in (doc.signatories or [])}
	added = 0
	for m in members:
		if m.name not in existing:
			doc.append("signatories", {"board_member": m.name, "signed": 0})
			added += 1

	doc.save(ignore_permissions=True)
	return {"added": added, "message": f"Loaded {added} board member(s) as signatories."}


@frappe.whitelist()
def send_circulation_notice(resolution_name):
	"""Email the resolution text to every signatory for review and signing."""
	doc = frappe.get_doc("Board Resolution", resolution_name)
	if not doc.signatories:
		frappe.throw(_("No signatories on this resolution. Use Load Board Members as Signatories first."))

	sent = 0
	for row in doc.signatories:
		email = frappe.db.get_value(
			"Board Member", row.board_member, "email"
		) if row.board_member else None
		if not email:
			continue
		frappe.sendmail(
			recipients=[email],
			subject=f"Written Resolution for Signature — {doc.resolution_title}",
			message=_build_circulation_html(doc),
			reference_doctype="Board Resolution",
			reference_name=resolution_name,
		)
		sent += 1

	if sent and not doc.circulation_date:
		doc.db_set("circulation_date", today())

	return {"sent": sent, "message": f"Circulation notice sent to {sent} signatory(ies)."}


@frappe.whitelist()
def send_signing_reminder(resolution_name):
	"""Remind signatories who have not yet signed."""
	doc = frappe.get_doc("Board Resolution", resolution_name)
	unsigned = [s for s in (doc.signatories or []) if not s.signed]
	if not unsigned:
		return {"sent": 0, "message": "All signatories have already signed."}

	sent = 0
	for row in unsigned:
		email = frappe.db.get_value(
			"Board Member", row.board_member, "email"
		) if row.board_member else None
		if not email:
			continue
		frappe.sendmail(
			recipients=[email],
			subject=f"Reminder: Signature Required — {doc.resolution_title}",
			message=_build_reminder_html(doc),
			reference_doctype="Board Resolution",
			reference_name=resolution_name,
		)
		sent += 1

	return {"sent": sent, "message": f"Signing reminder sent to {sent} outstanding signatory(ies)."}


def _build_circulation_html(doc):
	return f"""
    {email_header(doc.company, "Written Resolution for Signature")}
    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;
                  border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:20px">
        {info_row("Resolution", doc.resolution_title, highlight=True)}
        {info_row("Category", doc.resolution_category or "—")}
        {info_row("Signing Deadline", formatdate(doc.signing_deadline, "long") if doc.signing_deadline else "—")}
    </table>
    <p style="font-size:13px;color:#475569;line-height:1.7">
        Please review the attached resolution text and return your signed copy before the deadline above.
    </p>
    {cta_button(f"/app/board-resolution/{doc.name}", "Open Resolution")}
    {email_footer()}
    """


def _build_reminder_html(doc):
	return f"""
    {email_header(doc.company, "Signature Still Required")}
    <p style="font-size:13px;color:#1E293B;line-height:1.7">
        Our records show your signature is still outstanding on <b>{doc.resolution_title}</b>
        {f"— deadline: <b>{formatdate(doc.signing_deadline, 'long')}</b>" if doc.signing_deadline else ""}.
    </p>
    {cta_button(f"/app/board-resolution/{doc.name}", "Open Resolution", colour="#D97706")}
    {email_footer()}
    """
