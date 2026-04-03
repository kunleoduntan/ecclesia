# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/api/recruitment_portal_notifications.py

import frappe
from frappe.utils import today, add_days


def _url(path=""):
    return f"{frappe.utils.get_url()}{path}"


def _send(to, subject, body, ref_dt=None, ref_name=None):
    if not to:
        return
    try:
        frappe.sendmail(recipients=[to], subject=subject, message=body,
                        reference_doctype=ref_dt, reference_name=ref_name, now=True)
    except Exception as e:
        frappe.log_error(f"Recruitment email: {e}", "Recruitment Notifications")


# ── Doc Events ────────────────────────────────────────────────────────────────

def on_applicant_insert(doc, method=None):
    """Acknowledge receipt of application."""
    try:
        if not doc.email_id:
            return
        token = frappe.db.get_value("Job Applicant", doc.name, "ec_portal_token") or ""
        track_url = _url(f"/careers?token={token}") if token else _url("/careers")
        _send(
            doc.email_id,
            f"Application Received — {doc.job_title}",
            f"""
<p>Dear {doc.applicant_name},</p>
<p>Thank you for applying for <strong>{doc.job_title}</strong>. We have received your application and it is being reviewed.</p>
{f'<p>Use this token to track your application status: <strong style="font-family:monospace;font-size:16px">{token}</strong></p>' if token else ''}
<p style="margin-top:20px">
  <a href="{track_url}" style="background:#0a0f1e;color:white;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:600">Track Application →</a>
</p>
<p style="color:#64748b;font-size:12px;margin-top:20px">We aim to respond to all applications within 5 business days.</p>
            """,
            ref_dt="Job Applicant", ref_name=doc.name,
        )
    except Exception as e:
        frappe.log_error(f"on_applicant_insert: {e}", "Recruitment Notifications")


def on_applicant_update(doc, method=None):
    """Notify on meaningful status changes (handled by admin.update_applicant_status)."""
    pass  # Notifications sent directly from update_applicant_status


def on_interview_submit(doc, method=None):
    """Confirm interview to candidate on submit."""
    try:
        if not doc.job_applicant:
            return
        email = frappe.db.get_value("Job Applicant", doc.job_applicant, "email_id")
        name  = doc.applicant_name or frappe.db.get_value("Job Applicant", doc.job_applicant, "applicant_name")
        job   = frappe.db.get_value("Job Applicant", doc.job_applicant, "job_title")
        token = frappe.db.get_value("Job Applicant", doc.job_applicant, "ec_portal_token") or ""
        if not email:
            return
        meeting_line = f"<p>📹 Meeting Link: <a href='{doc.ec_meeting_link}'>{doc.ec_meeting_link}</a></p>" if doc.ec_meeting_link else ""
        _send(
            email,
            f"Interview Confirmed — {job}",
            f"""
<p>Dear {name},</p>
<p>Your interview for <strong>{job}</strong> has been confirmed.</p>
<table style="border-collapse:collapse;max-width:420px;width:100%;margin:16px 0">
  <tr><td style="padding:8px 0;color:#64748b">Date</td><td><strong>{doc.scheduled_on}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#64748b">Time</td><td><strong>{doc.from_time} – {doc.to_time}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#64748b">Round</td><td>{doc.interview_round}</td></tr>
</table>
{meeting_line}
<p style="margin-top:20px"><a href="{_url(f'/careers?token={token}')}" style="background:#0a0f1e;color:white;padding:10px 22px;border-radius:8px;text-decoration:none">View Application</a></p>
            """,
            ref_dt="Interview", ref_name=doc.name,
        )
    except Exception as e:
        frappe.log_error(f"on_interview_submit: {e}", "Recruitment Notifications")


def on_interview_update(doc, method=None):
    """Notify candidate if interview is rescheduled or cancelled."""
    try:
        prev = doc.get_doc_before_save()
        if not prev or prev.status == doc.status:
            return
        if doc.status not in ("Cancelled", "Completed"):
            return
        email = frappe.db.get_value("Job Applicant", doc.job_applicant, "email_id")
        if not email:
            return
        _send(
            email,
            f"Interview {doc.status} — {doc.applicant_name}",
            f"<p>Dear {doc.applicant_name},</p><p>Your interview scheduled for {doc.scheduled_on} has been marked as <strong>{doc.status}</strong>. Our team will be in touch if a rescheduling is needed.</p>",
            ref_dt="Interview", ref_name=doc.name,
        )
    except Exception as e:
        frappe.log_error(f"on_interview_update: {e}", "Recruitment Notifications")


# ── Scheduled Tasks ───────────────────────────────────────────────────────────

def send_application_followups():
    """
    Daily: remind HR of applications pending review for more than 5 days.
    Also: remind applicants who started but did not complete (if using multi-step flow).
    """
    try:
        cutoff = add_days(today(), -5)
        pending = frappe.db.sql("""
            SELECT name, applicant_name, email_id, job_title, creation
            FROM `tabJob Applicant`
            WHERE status = 'Open'
              AND DATE(creation) <= %s
              AND ec_applied_via_portal = 1
        """, cutoff, as_dict=True)

        if not pending:
            return

        # Notify HR
        hr_managers = frappe.db.sql("""
            SELECT DISTINCT u.email
            FROM `tabUser` u
            JOIN `tabHas Role` r ON r.parent = u.name
            WHERE r.role IN ('HR Manager','HR User')
              AND u.enabled = 1
        """, as_dict=True)

        if pending and hr_managers:
            hr_emails = [m.email for m in hr_managers]
            rows = "".join(
                f"<tr><td style='padding:6px 8px;border-bottom:1px solid #e2e8f0'>{p.applicant_name}</td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e2e8f0'>{p.job_title}</td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e2e8f0'>{str(p.creation)[:10]}</td></tr>"
                for p in pending
            )
            for email in hr_emails:
                _send(
                    email,
                    f"⏰ {len(pending)} Applicant(s) Awaiting Review",
                    f"""
<p>The following portal applications have been waiting for more than 5 days:</p>
<table style="border-collapse:collapse;width:100%;max-width:520px;border:1px solid #e2e8f0">
  <thead><tr style="background:#f1f5f9"><th style="padding:8px;text-align:left">Applicant</th><th>Position</th><th>Applied</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<p style="margin-top:16px"><a href="{_url('/recruitment')}" style="background:#0a0f1e;color:white;padding:10px 20px;border-radius:8px;text-decoration:none">Open Recruitment Dashboard</a></p>
                    """,
                )
    except Exception as e:
        frappe.log_error(f"send_application_followups: {e}", "Recruitment Notifications")