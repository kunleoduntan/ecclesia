# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/api/recruitment_portal_jobs.py
# Public-facing job listing API — no login required for read

import frappe
from frappe.utils import today, getdate


@frappe.whitelist(allow_guest=True)
def get_jobs(department=None, designation=None, search=None, page=1, page_size=20):
    """Public job listing — only Open + Published jobs."""
    filters = {
        "status": "Open",
        "ec_portal_published": 1,
    }
    if department:
        filters["department"] = department
    if designation:
        filters["designation"] = designation

    start = (int(page) - 1) * int(page_size)

    rows = frappe.get_all(
        "Job Opening",
        filters=filters,
        fields=["name", "job_title", "department", "designation", "location",
                "description", "ec_skills_required", "ec_experience_years_min",
                "ec_education_level", "ec_salary_min", "ec_salary_max",
                "ec_application_deadline", "posted_on"],
        order_by="posted_on desc",
        limit=int(page_size), start=start,
    )

    if search:
        s = search.lower()
        rows = [r for r in rows if
                s in (r.job_title or "").lower() or
                s in (r.department or "").lower() or
                s in (r.ec_skills_required or "").lower() or
                s in (r.description or "").lower()]

    # Mark expired
    today_d = getdate(today())
    for r in rows:
        r["is_expired"] = bool(
            r.ec_application_deadline and
            getdate(r.ec_application_deadline) < today_d
        )

    total = frappe.db.count("Job Opening", {"status": "Open", "ec_portal_published": 1})
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist(allow_guest=True)
def get_job_detail(name):
    """Full job details including screening questions (without correct answers)."""
    doc = frappe.db.get_value(
        "Job Opening", name,
        ["name", "job_title", "department", "designation", "location",
         "description", "ec_skills_required", "ec_experience_years_min",
         "ec_education_level", "ec_salary_min", "ec_salary_max",
         "ec_application_deadline", "ec_scoring_enabled",
         "ec_screening_questions", "posted_on", "status", "ec_portal_published"],
        as_dict=True,
    )
    if not doc or not doc.ec_portal_published:
        frappe.throw("Job not found", frappe.DoesNotExistError)

    # Parse screening questions — strip correct_answer field for public
    questions = []
    if doc.ec_screening_questions:
        import json
        try:
            raw = json.loads(doc.ec_screening_questions)
            for q in raw:
                questions.append({
                    "id":       q.get("id"),
                    "question": q.get("question"),
                    "type":     q.get("type", "text"),   # text, yesno, mcq, rating
                    "options":  q.get("options", []),
                    "required": q.get("required", True),
                    "weight":   q.get("weight", 0),
                })
        except Exception:
            pass

    return {
        "name":                 doc.name,
        "job_title":            doc.job_title,
        "department":           doc.department,
        "designation":          doc.designation,
        "location":             doc.location,
        "description":          doc.description,
        "ec_skills_required":   doc.ec_skills_required,
        "ec_experience_years_min": doc.ec_experience_years_min,
        "ec_education_level":   doc.ec_education_level,
        "ec_salary_min":        doc.ec_salary_min,
        "ec_salary_max":        doc.ec_salary_max,
        "ec_application_deadline": str(doc.ec_application_deadline) if doc.ec_application_deadline else None,
        "posted_on":            str(doc.posted_on) if doc.posted_on else None,
        "screening_questions":  questions,
        "has_screening":        len(questions) > 0,
        "status":               doc.status,
    }


@frappe.whitelist(allow_guest=True)
def get_departments():
    rows = frappe.db.sql("""
        SELECT DISTINCT department FROM `tabJob Opening`
        WHERE status='Open' AND ec_portal_published=1 AND department IS NOT NULL
        ORDER BY department
    """, as_dict=True)
    return [r.department for r in rows]


@frappe.whitelist(allow_guest=True)
def get_application_status(token):
    """Track application status by portal token — no login required."""
    if not token:
        frappe.throw("Invalid tracking token")
    app = frappe.db.get_value(
        "Job Applicant",
        {"ec_portal_token": token},
        ["name", "applicant_name", "job_title", "status",
         "ec_total_score", "ec_scoring_status", "ec_applied_via_portal",
         "creation", "ec_interview_slot",
         "ec_knockout_passed", "ec_knockout_failed_reason",
         "ec_is_duplicate"],
        as_dict=True,
    )
    if not app:
        frappe.throw("Application not found", frappe.DoesNotExistError)

    # Interview info if any
    interview = None
    if frappe.db.has_column("Job Applicant", "ec_interview_slot") and app.get("ec_interview_slot"):
        interview = {"scheduled_at": str(app.ec_interview_slot)}
    else:
        intvw = frappe.db.get_value(
            "Interview",
            {"job_applicant": app.name, "status": ["!=", "Cancelled"]},
            ["name", "scheduled_on", "from_time", "ec_meeting_link", "status"],
            as_dict=True,
        )
        if intvw:
            interview = dict(intvw)

    # Pipeline stages (ordered)
    stages = ["Open", "Replied", "Hold", "Accepted", "Rejected"]
    stage_labels = {
        "Open":     "Application Received",
        "Replied":  "Under Review",
        "Hold":     "Shortlisted",
        "Accepted": "Offer Extended",
        "Rejected": "Not Shortlisted",
    }
    current = app.status or "Open"
    stage_idx = stages.index(current) if current in stages else 0

    is_ko  = app.ec_scoring_status == "Knocked Out"
    is_dup = bool(app.ec_is_duplicate)

    return {
        "applicant_name":       app.applicant_name,
        "job_title":            app.job_title,
        "status":               app.status,
        "status_label":         stage_labels.get(app.status, app.status),
        "stage_index":          stage_idx,
        "stages":               [{"key": s, "label": stage_labels[s]} for s in stages],
        "applied_on":           str(app.creation)[:10],
        "ec_total_score":       float(app.ec_total_score or 0),
        "scoring_complete":     app.ec_scoring_status == "Scored",
        "interview":            interview,
        "knockout_failed":      is_ko,
        "knockout_reason":      app.ec_knockout_failed_reason or "",
        "is_duplicate":         is_dup,
    }