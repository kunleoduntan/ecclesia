# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/annual_general_meeting/annual_general_meeting.py
"""
Annual General Meeting — Controller
=====================================
Business logic for CAMA 2020 compliant AGM management.

Key statutory references (CAMA 2020 — Companies and Allied Matters Act):
  s.237 — Private companies must hold AGM within 15 months of last AGM
  s.239 — AGM notice: minimum 21 clear days for shareholders
  s.244 — Quorum: 2 members personally present (unless articles differ)
  s.265 — Minutes to be kept and signed by chairman within 30 days
  s.370 — Annual return to CAC: 42 days after AGM (private company)
  s.438 — Penalty for failure to hold AGM: fine on company and officers
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    date_diff, today, add_days, getdate, nowdate, cint, flt
)


class AnnualGeneralMeeting(Document):

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def validate(self):
        self._validate_notice_period()
        self._validate_agm_date()
        self._compute_analytics()
        self._set_quorum_check()
        self._compute_proxy_count()
        self._set_cac_deadline()
        self._check_late_filing()

    def on_submit(self):
        self._send_submission_notification()

    def on_cancel(self):
        frappe.msgprint(_("AGM cancelled. Ensure CAC is informed if notices were already dispatched."),
                        indicator="orange")

    # ── Validation methods ────────────────────────────────────────────────────

    def _validate_notice_period(self):
        """CAMA 2020 s.239: AGM requires minimum 21 clear days notice."""
        if not self.notice_date or not self.agm_date:
            return
        days = date_diff(self.agm_date, self.notice_date)
        self.notice_days = days
        min_days = 21 if self.agm_type == "Annual General Meeting" else 14
        self.notice_compliant = 1 if days >= min_days else 0
        if days < min_days and self.docstatus == 0:
            frappe.msgprint(
                _(f"Notice period is only {days} days. CAMA 2020 requires minimum "
                  f"{min_days} clear days notice for {self.agm_type}. "
                  f"Consider rescheduling or obtaining shareholder consent to short notice."),
                indicator="orange", title="Notice Period Warning"
            )

    def _validate_agm_date(self):
        """Warn if AGM is more than 15 months after the previous AGM."""
        if not self.agm_date or self.agm_type != "Annual General Meeting":
            return
        # Look for previous AGM for this company
        prev = frappe.db.get_all(
            "Annual General Meeting",
            filters={
                "company": self.company,
                "agm_type": "Annual General Meeting",
                "status": ["in", ["Held","Minutes Approved","CAC Filed","Closed"]],
                "name": ["!=", self.name or ""],
            },
            fields=["agm_date"],
            order_by="agm_date desc",
            limit=1,
        )
        if prev:
            last_agm = getdate(prev[0].agm_date)
            gap_days = date_diff(self.agm_date, last_agm)
            if gap_days > 457:   # 15 months ≈ 457 days
                frappe.msgprint(
                    _(f"This AGM is {gap_days} days after the last AGM ({last_agm}). "
                      "CAMA 2020 s.237 requires AGM within 15 months of the previous one. "
                      "Late holding of AGM is a regulatory breach — consider whether an "
                      "extension application to CAC is needed."),
                    indicator="red", title="CAMA 2020 — AGM Deadline Breach"
                )

    def _compute_analytics(self):
        """Compute days_to_agm and days_overdue."""
        if not self.agm_date:
            return
        agm = getdate(self.agm_date)
        today_date = getdate(today())
        diff = date_diff(agm, today_date)
        self.days_to_agm = max(0, diff) if diff >= 0 else 0
        self.days_overdue = max(0, -diff) if diff < 0 else 0
        if self.notice_date:
            self.days_notice_given = date_diff(self.agm_date, self.notice_date)

    def _set_quorum_check(self):
        """Auto-set quorum_met based on shareholders_present vs quorum_required."""
        req = cint(self.quorum_required) or 2
        present = cint(self.shareholders_present) or 0
        if present > 0:
            self.quorum_met = 1 if present >= req else 0
        # Calculate % shares represented
        if cint(self.total_shares) > 0 and cint(self.shares_represented) > 0:
            self.quorum_percentage = flt(self.shares_represented) / flt(self.total_shares) * 100

    def _compute_proxy_count(self):
        """Count proxy forms received and update proxies_received."""
        if self.proxies:
            valid_proxies = [p for p in self.proxies if (p.status or "Received") != "Rejected"]
            self.proxies_received = len(valid_proxies)

    def _set_cac_deadline(self):
        """CAMA 2020 s.370: Annual return due 42 days after AGM for private company."""
        if self.agm_date and self.agm_type == "Annual General Meeting" and not self.cac_filing_deadline:
            self.cac_filing_deadline = add_days(self.agm_date, 42)

    def _check_late_filing(self):
        """Flag if CAC was filed after the 42-day deadline."""
        if self.cac_filing_date and self.cac_filing_deadline:
            self.late_filing_flag = 1 if getdate(self.cac_filing_date) > getdate(self.cac_filing_deadline) else 0

    def _send_submission_notification(self):
        """Notify company secretary and chairperson when AGM is submitted."""
        recipients = []
        if self.company_secretary:
            email = frappe.db.get_value("Employee", self.company_secretary, "company_email") or \
                    frappe.db.get_value("Employee", self.company_secretary, "personal_email")
            if email:
                recipients.append(email)
        if recipients:
            frappe.sendmail(
                recipients=recipients,
                subject=f"AGM Submitted — {self.agm_title}",
                message=f"""
<p>The Annual General Meeting record <b>{self.agm_title}</b> has been submitted.</p>
<ul>
  <li><b>Company:</b> {self.company}</li>
  <li><b>AGM Date:</b> {self.agm_date}</li>
  <li><b>Venue:</b> {self.venue or 'Virtual'}</li>
  <li><b>Status:</b> {self.status}</li>
  <li><b>CAC Filing Deadline:</b> {self.cac_filing_deadline or 'N/A'}</li>
</ul>
<p>Please ensure all statutory notices are sent and proxy forms are collected.</p>
<p><em>Ecclesia ERP — Value Impacts Consulting</em></p>
""",
                reference_doctype=self.doctype,
                reference_name=self.name,
            )


# ── Whitelisted API methods ───────────────────────────────────────────────────

@frappe.whitelist()
def send_agm_notices(agm_name, channel="Email"):
    """
    Send AGM notices to all shareholders in the notice_logs child table.
    Can be triggered from the JS 'Send Notices' button.
    """
    agm = frappe.get_doc("Annual General Meeting", agm_name)

    if not agm.notice_logs:
        frappe.throw(_("No notice recipients found. Add shareholders to the Notice Delivery Log first."))

    sent = 0
    failed = 0

    for row in agm.notice_logs:
        if row.delivery_status in ("Delivered", "Sent"):
            continue
        if channel == "Email" and not row.email:
            row.delivery_status = "Failed"
            row.remarks = "No email address"
            failed += 1
            continue
        try:
            frappe.sendmail(
                recipients=[row.email],
                subject=f"Notice of Annual General Meeting — {agm.company}",
                message=_build_agm_notice_email(agm),
                reference_doctype="Annual General Meeting",
                reference_name=agm_name,
            )
            row.delivery_status = "Sent"
            row.sent_date = today()
            sent += 1
        except Exception as e:
            row.delivery_status = "Failed"
            row.remarks = str(e)[:200]
            failed += 1

    agm.members_notified = sent
    if sent > 0:
        agm.status = "Notices Sent"
    agm.save(ignore_permissions=True)

    return {
        "sent": sent,
        "failed": failed,
        "total": len(agm.notice_logs),
        "message": f"Notices sent: {sent}. Failed: {failed}."
    }


@frappe.whitelist()
def get_agm_compliance_summary(agm_name):
    """Return a compliance checklist for the AGM (used in JS dashboard)."""
    agm = frappe.get_doc("Annual General Meeting", agm_name)
    today_date = getdate(today())

    checks = []

    # 1. Notice period
    if agm.notice_date and agm.agm_date:
        days = date_diff(agm.agm_date, agm.notice_date)
        min_days = 21 if agm.agm_type == "Annual General Meeting" else 14
        checks.append({
            "item":   "AGM Notice Period",
            "status": "Pass" if days >= min_days else "Fail",
            "detail": f"{days} days given (minimum {min_days} required — CAMA 2020 s.239)",
        })
    else:
        checks.append({"item":"AGM Notice Period","status":"Pending","detail":"Notice date not set"})

    # 2. Quorum
    checks.append({
        "item":   "Quorum",
        "status": "Pass" if agm.quorum_met else ("Pending" if not agm.shareholders_present else "Fail"),
        "detail": f"{agm.shareholders_present or 0} present vs {agm.quorum_required or 2} required",
    })

    # 3. Proxy forms
    checks.append({
        "item":   "Proxy Forms",
        "status": "Pass" if cint(agm.proxies_received) >= 0 else "Pending",
        "detail": f"{agm.proxies_received or 0} proxy forms received",
    })

    # 4. Financial statements attached
    checks.append({
        "item":   "Financial Statements",
        "status": "Pass" if agm.financial_statements else "Pending",
        "detail": "Accounts attached" if agm.financial_statements else "Not yet attached",
    })

    # 5. Signed minutes
    checks.append({
        "item":   "Signed Minutes",
        "status": "Pass" if agm.signed_minutes else "Pending",
        "detail": "Minutes signed and attached" if agm.signed_minutes else
                  "CAMA 2020 s.265: Chairman must sign minutes within 30 days",
    })

    # 6. CAC Annual Return
    if agm.cac_filing_required:
        if agm.cac_filed:
            status = "Pass"
            detail = f"Filed {agm.cac_filing_date} — Ref: {agm.cac_reference or 'N/A'}"
        elif agm.cac_filing_deadline and getdate(agm.cac_filing_deadline) < today_date:
            status = "Fail"
            detail = f"Overdue since {agm.cac_filing_deadline} — CAMA 2020 s.370"
        else:
            status = "Pending"
            detail = f"Due: {agm.cac_filing_deadline or 'Set AGM date first'}"
        checks.append({"item":"CAC Annual Return Filing","status":status,"detail":detail})

    # 7. Resolutions outcome
    if agm.resolutions:
        passed = sum(1 for r in agm.resolutions if r.result == "Passed")
        failed_ = sum(1 for r in agm.resolutions if r.result == "Defeated")
        checks.append({
            "item":"Resolutions",
            "status":"Pass",
            "detail":f"{passed} passed, {failed_} defeated, {len(agm.resolutions)-passed-failed_} pending",
        })
    else:
        checks.append({"item":"Resolutions","status":"Pending","detail":"No resolutions recorded yet"})

    return {"checks": checks, "agm": agm.as_dict()}


@frappe.whitelist()
def generate_notice_recipients_from_shareholders(agm_name):
    """
    Auto-populate the Notice Log from the company's registered shareholders
    (reads from Statutory Register Entry where register_type = Register of Members).
    """
    agm = frappe.get_doc("Annual General Meeting", agm_name)

    members = frappe.db.get_all(
        "Statutory Register Entry",
        filters={
            "company": agm.company,
            "register_type": "Register of Members",
        },
        fields=["party_name", "address"],
        limit=500,
    )

    if not members:
        return {"added": 0, "message": "No entries found in Register of Members"}

    existing = {row.shareholder_name for row in (agm.notice_logs or [])}
    added = 0
    for m in members:
        if m.party_name not in existing:
            agm.append("notice_logs", {
                "shareholder_name": m.party_name,
                "notice_channel": "Email",
                "delivery_status": "Pending",
            })
            added += 1

    agm.save(ignore_permissions=True)
    return {"added": added, "message": f"Added {added} shareholders to notice log"}


def _build_agm_notice_email(agm):
    """Build the HTML email body for AGM notices."""
    agenda_html = ""
    if agm.agenda_items:
        items = "".join(
            f"<li><b>{a.item_no}.</b> {a.agenda_title} ({a.agenda_type})</li>"
            for a in sorted(agm.agenda_items, key=lambda x: x.item_no or 0)
        )
        agenda_html = f"<ol>{items}</ol>"
    else:
        agenda_html = "<p>Agenda to follow.</p>"

    venue_html = (
        f"<b>Venue:</b> {agm.venue}<br>" if agm.venue_type == "Physical"
        else f"<b>Platform:</b> {agm.virtual_platform or 'Online'} — {agm.virtual_link or 'Link to follow'}<br>"
    )

    return f"""
<p>Dear Shareholder,</p>
<p>You are hereby notified that the <b>{agm.agm_type}</b> of <b>{agm.company}</b>
will be held as follows:</p>
<table style="border-collapse:collapse;width:100%;font-size:14px">
  <tr><td style="padding:6px;font-weight:bold;width:160px">Date:</td>
      <td style="padding:6px">{agm.agm_date}</td></tr>
  <tr><td style="padding:6px;font-weight:bold">Time:</td>
      <td style="padding:6px">{agm.agm_time or 'To be advised'}</td></tr>
  <tr><td style="padding:6px;font-weight:bold">Mode:</td>
      <td style="padding:6px">{agm.venue_type}</td></tr>
  <tr><td style="padding:6px;font-weight:bold">{'Venue' if agm.venue_type=='Physical' else 'Platform'}:</td>
      <td style="padding:6px">{agm.venue or agm.virtual_link or 'To be confirmed'}</td></tr>
</table>
<h4>Agenda</h4>
{agenda_html}
<h4>Proxy</h4>
<p>A member entitled to attend and vote is entitled to appoint a proxy to attend and vote instead.
A proxy need not be a member. Proxy forms must be returned to the Company Secretary
at least 48 hours before the meeting.</p>
<p>Please find the proxy form attached.</p>
<p>By Order of the Board,<br>
<b>The Company Secretary</b><br>
{agm.company}</p>
<hr>
<p style="font-size:11px;color:#888">
This notice is issued in compliance with CAMA 2020 and the Company's Articles of Association.<br>
Ecclesia ERP — Value Impacts Consulting</p>
"""
