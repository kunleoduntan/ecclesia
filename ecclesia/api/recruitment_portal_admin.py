# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/api/recruitment_portal_admin.py
# HR Admin API — job management, criteria, shortlisting, interviews

import frappe
import json
from frappe.utils import flt, today, now


def _require_hr():
    if frappe.session.user == "Guest":
        frappe.throw("Login required", frappe.AuthenticationError)
    roles = frappe.get_roles(frappe.session.user)
    if not any(r in roles for r in ["HR Manager", "HR User", "System Manager", "Recruitment Manager"]):
        frappe.throw("HR access required", frappe.PermissionError)


# ── JOB OPENINGS ──────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_job_openings(status=None, page=1, page_size=20):
    _require_hr()
    filters = {}
    if status and status != "All":
        filters["status"] = status
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all(
        "Job Opening",
        filters=filters,
        fields=["name", "job_title", "department", "designation", "status",
                "posted_on", "ec_portal_published", "ec_scoring_enabled",
                "ec_pass_score", "ec_application_deadline"],
        order_by="posted_on desc",
        limit=int(page_size), start=start,
    )
    for r in rows:
        r["applicant_count"] = frappe.db.count("Job Applicant", {"job_title": r.name})
        r["shortlisted_count"] = frappe.db.count("Job Applicant", {"job_title": r.name, "status": "Hold"})
    total = frappe.db.count("Job Opening", filters)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist()
def save_job_criteria(job_opening, criteria):
    """
    Save scoring criteria + screening questions for a Job Opening.
    criteria = {
        ec_skills_required, ec_experience_years_min, ec_education_level,
        ec_salary_min, ec_salary_max, ec_scoring_enabled, ec_pass_score,
        ec_weight_education, ec_weight_experience, ec_weight_skills, ec_weight_screening,
        ec_screening_questions (JSON array), ec_application_deadline, ec_portal_published
    }
    """
    _require_hr()
    if not frappe.db.exists("Job Opening", job_opening):
        frappe.throw("Job Opening not found")
    if isinstance(criteria, str):
        criteria = json.loads(criteria)

    # Validate weights sum
    weights = [
        flt(criteria.get("ec_weight_education", 20)),
        flt(criteria.get("ec_weight_experience", 30)),
        flt(criteria.get("ec_weight_skills", 30)),
        flt(criteria.get("ec_weight_screening", 20)),
    ]
    total_w = sum(weights)
    if total_w > 0 and abs(total_w - 100) > 1:
        frappe.throw(f"Scoring weights must sum to 100 (current sum: {total_w})")

    # Validate screening questions JSON
    if criteria.get("ec_screening_questions"):
        try:
            q = json.loads(criteria["ec_screening_questions"]) if isinstance(criteria["ec_screening_questions"], str) else criteria["ec_screening_questions"]
            criteria["ec_screening_questions"] = json.dumps(q)
        except Exception:
            frappe.throw("Screening questions must be valid JSON")

    allowed = [
        "ec_skills_required", "ec_nice_to_have_skills",
        "ec_experience_years_min", "ec_experience_years_max",
        "ec_education_level", "ec_field_of_study",
        "ec_required_certifications", "ec_preferred_certifications",
        "ec_required_industry", "ec_related_industries",
        "ec_location_mode", "ec_required_location_city", "ec_required_location_country",
        "ec_required_languages",
        "ec_min_stability_years",
        "ec_portfolio_required",
        "ec_salary_min", "ec_salary_max",
        "ec_scoring_enabled", "ec_pass_score", "ec_auto_reject_below",
        "ec_weight_education", "ec_weight_experience", "ec_weight_skills",
        "ec_weight_certifications", "ec_weight_industry", "ec_weight_location",
        "ec_weight_languages", "ec_weight_stability", "ec_weight_portfolio",
        "ec_weight_screening",
        "ec_screening_questions", "ec_application_deadline", "ec_portal_published",
    ]
    update = {k: v for k, v in criteria.items() if k in allowed}
    if update:
        frappe.db.set_value("Job Opening", job_opening, update)
    frappe.db.commit()
    return {"status": "saved"}


@frappe.whitelist()
def get_job_criteria(job_opening):
    _require_hr()
    job = frappe.db.get_value(
        "Job Opening", job_opening,
        ["name", "job_title", "department", "designation", "status",
         "ec_skills_required", "ec_nice_to_have_skills",
         "ec_experience_years_min", "ec_experience_years_max",
         "ec_education_level", "ec_field_of_study",
         "ec_required_certifications", "ec_preferred_certifications",
         "ec_required_industry", "ec_related_industries",
         "ec_location_mode", "ec_required_location_city", "ec_required_location_country",
         "ec_required_languages",
         "ec_min_stability_years",
         "ec_portfolio_required",
         "ec_salary_min", "ec_salary_max",
         "ec_scoring_enabled", "ec_pass_score", "ec_auto_reject_below",
         "ec_weight_education", "ec_weight_experience", "ec_weight_skills",
         "ec_weight_certifications", "ec_weight_industry", "ec_weight_location",
         "ec_weight_languages", "ec_weight_stability", "ec_weight_portfolio",
         "ec_weight_screening",
         "ec_screening_questions", "ec_application_deadline", "ec_portal_published"],
        as_dict=True,
    )
    if not job:
        frappe.throw("Job Opening not found")
    questions = []
    if job.ec_screening_questions:
        try:
            questions = json.loads(job.ec_screening_questions)
        except Exception:
            pass
    return dict(job) | {"screening_questions_parsed": questions}


# ── APPLICANTS & SHORTLISTING ─────────────────────────────────────────────────

@frappe.whitelist()
def get_applicants(job_opening=None, status=None, min_score=None, page=1, page_size=30):
    _require_hr()
    filters = {}
    if job_opening:
        filters["job_title"] = job_opening
    if status and status != "All":
        filters["status"] = status
    start = (int(page) - 1) * int(page_size)

    rows = frappe.get_all(
        "Job Applicant",
        filters=filters,
        fields=["name", "applicant_name", "email_id", "phone_number",
                "job_title", "status", "creation",
                "ec_total_score", "ec_scoring_status",
                "ec_education_level", "ec_field_of_study", "ec_experience_years",
                "ec_skills", "ec_certifications", "ec_industry_experience",
                "ec_current_city", "ec_current_country",
                "ec_languages", "ec_portfolio_url", "ec_github_url",
                "ec_knockout_passed", "ec_knockout_failed_reason",
                "ec_is_duplicate", "ec_duplicate_of",
                "ec_cv_file", "ec_applied_via_portal", "ec_portal_token"],
        order_by="ec_total_score desc, creation asc",
        limit=int(page_size), start=start,
    )

    if min_score is not None:
        rows = [r for r in rows if flt(r.ec_total_score) >= flt(min_score)]

    # Fetch pass score per job for colour coding
    pass_scores = {}
    job_names = list({r.job_title for r in rows})
    for jn in job_names:
        ps = frappe.db.get_value("Job Opening", jn, "ec_pass_score") or 70
        pass_scores[jn] = flt(ps)

    for r in rows:
        r["passes"] = flt(r.ec_total_score) >= pass_scores.get(r.job_title, 70)
        r["pass_score"] = pass_scores.get(r.job_title, 70)

    total = frappe.db.count("Job Applicant", filters)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist()
def update_applicant_status(job_applicant, status):
    _require_hr()
    valid = ["Open", "Replied", "Hold", "Accepted", "Rejected"]
    if status not in valid:
        frappe.throw(f"Status must be one of: {', '.join(valid)}")
    frappe.db.set_value("Job Applicant", job_applicant, "status", status)
    frappe.db.commit()

    # Notify applicant
    try:
        _notify_status_change(job_applicant, status)
    except Exception:
        pass
    return {"status": "updated"}


@frappe.whitelist()
def bulk_update_status(job_applicants, status):
    _require_hr()
    if isinstance(job_applicants, str):
        job_applicants = json.loads(job_applicants)
    for name in job_applicants:
        frappe.db.set_value("Job Applicant", name, "status", status)
    frappe.db.commit()
    return {"updated": len(job_applicants)}


# ── INTERVIEW SCHEDULING ──────────────────────────────────────────────────────

@frappe.whitelist()
def schedule_interview(job_applicant, scheduled_on, from_time, to_time,
                        interview_round=None, interviewers=None, meeting_link=None):
    """Create an ERPNext Interview record and notify the candidate."""
    _require_hr()
    app = frappe.get_doc("Job Applicant", job_applicant)

    intvw = frappe.get_doc({
        "doctype":        "Interview",
        "job_applicant":  job_applicant,
        "applicant_name": app.applicant_name,
        "designation":    frappe.db.get_value("Job Opening", app.job_title, "designation") or "",
        "interview_round":interview_round or "Technical",
        "scheduled_on":   scheduled_on,
        "from_time":      from_time,
        "to_time":        to_time,
        "status":         "Scheduled",
        "ec_meeting_link":meeting_link or "",
    })

    # Add interviewers
    if interviewers:
        if isinstance(interviewers, str):
            interviewers = json.loads(interviewers)
        for i in interviewers:
            intvw.append("interview_details", {
                "interviewer": i,
            })

    intvw.insert(ignore_permissions=True)
    frappe.db.commit()

    # Update applicant status to Replied (under review)
    frappe.db.set_value("Job Applicant", job_applicant, "status", "Replied")

    # Notify candidate
    try:
        _notify_interview_scheduled(app, intvw)
    except Exception:
        pass

    return {"interview": intvw.name, "status": "scheduled"}


@frappe.whitelist()
def get_interviews(job_opening=None, page=1, page_size=20):
    _require_hr()
    filters = {"status": ["!=", "Cancelled"]}
    if job_opening:
        apps = frappe.db.sql("""
            SELECT name FROM `tabJob Applicant` WHERE job_title=%s
        """, job_opening, as_dict=True)
        app_names = [a.name for a in apps]
        if not app_names:
            return {"data": [], "total": 0}
        filters["job_applicant"] = ["in", app_names]

    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all(
        "Interview",
        filters=filters,
        fields=["name", "applicant_name", "job_applicant", "interview_round",
                "scheduled_on", "from_time", "to_time", "status",
                "ec_meeting_link"],
        order_by="scheduled_on desc",
        limit=int(page_size), start=start,
    )
    total = frappe.db.count("Interview", filters)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist()
def get_dashboard_stats():
    _require_hr()
    total_open   = frappe.db.count("Job Opening", {"status": "Open"})
    total_apps   = frappe.db.count("Job Applicant", {})
    new_today    = frappe.db.count("Job Applicant", {"creation": [">=", today()]})
    shortlisted  = frappe.db.count("Job Applicant", {"status": "Hold"})
    interviews_upcoming = frappe.db.count("Interview", {
        "status": "Scheduled",
        "scheduled_on": [">=", today()],
    })
    offers       = frappe.db.count("Job Applicant", {"status": "Accepted"})
    rejected     = frappe.db.count("Job Applicant", {"status": "Rejected"})

    # Average score
    avg = frappe.db.sql("""
        SELECT AVG(ec_total_score) FROM `tabJob Applicant`
        WHERE ec_scoring_status='Scored'
    """)[0][0]

    knocked_out = frappe.db.count("Job Applicant", {"ec_scoring_status": "Knocked Out"})
    duplicates  = frappe.db.count("Job Applicant", {"ec_is_duplicate": 1})

    return {
        "total_open":   total_open,
        "total_apps":   total_apps,
        "new_today":    new_today,
        "shortlisted":  shortlisted,
        "interviews":   interviews_upcoming,
        "offers":       offers,
        "rejected":     rejected,
        "avg_score":    round(flt(avg), 1),
        "knocked_out":  knocked_out,
        "duplicates":   duplicates,
    }


# ── Private helpers ───────────────────────────────────────────────────────────

def _notify_status_change(job_applicant, new_status):
    app = frappe.db.get_value("Job Applicant", job_applicant,
        ["applicant_name", "email_id", "job_title", "ec_portal_token"], as_dict=True)
    if not app or not app.email_id:
        return

    messages = {
        "Hold":     ("Your application has been shortlisted!", "Congratulations! Your application has been shortlisted for further consideration."),
        "Accepted": ("Congratulations — Offer Extended!", "We are pleased to inform you that we would like to extend an offer for this position. Our HR team will be in touch shortly with the details."),
        "Rejected": ("Application Update", "Thank you for your interest. After careful consideration, we regret to inform you that we will not be proceeding with your application at this time."),
        "Replied":  ("Application Update", "Your application is currently under review. We will contact you shortly with next steps."),
    }
    if new_status not in messages:
        return

    subject, body = messages[new_status]
    track_url = f"{frappe.utils.get_url()}/careers/track?token={app.ec_portal_token}"
    frappe.sendmail(
        recipients=[app.email_id],
        subject=f"{subject} — {app.job_title}",
        message=f"""
<p>Dear {app.applicant_name},</p>
<p>{body}</p>
<p>Position: <strong>{app.job_title}</strong></p>
<p><a href="{track_url}" style="background:#0f172a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;margin-top:8px">Track Your Application</a></p>
        """,
        now=True,
    )


def _notify_interview_scheduled(app_doc, interview_doc):
    if not app_doc.email_id:
        return
    track_url = f"{frappe.utils.get_url()}/careers/track?token={app_doc.ec_portal_token}"
    meeting_info = f"<p>Meeting Link: <a href='{interview_doc.ec_meeting_link}'>{interview_doc.ec_meeting_link}</a></p>" if interview_doc.ec_meeting_link else ""
    frappe.sendmail(
        recipients=[app_doc.email_id],
        subject=f"Interview Scheduled — {app_doc.job_title}",
        message=f"""
<p>Dear {app_doc.applicant_name},</p>
<p>We are pleased to invite you for an interview for the position of <strong>{app_doc.job_title}</strong>.</p>
<table style="border-collapse:collapse;max-width:400px;width:100%">
  <tr><td style="padding:8px 0;color:#64748b">Date</td><td><strong>{interview_doc.scheduled_on}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#64748b">Time</td><td><strong>{interview_doc.from_time} — {interview_doc.to_time}</strong></td></tr>
  <tr><td style="padding:8px 0;color:#64748b">Round</td><td>{interview_doc.interview_round}</td></tr>
</table>
{meeting_info}
<p><a href="{track_url}" style="background:#0f172a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;margin-top:12px">View Application Status</a></p>
        """,
        now=True,
    )