# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/api/recruitment_portal_apply.py
# Handles full 10-criteria application submission

import frappe
import json
import uuid
from frappe.utils import today, getdate


@frappe.whitelist(allow_guest=True)
def submit_application(
    job_opening,
    applicant_name,
    email_id,
    # Criteria 1 — Education
    education_level=None,
    field_of_study=None,
    university_name=None,
    graduation_year=None,
    # Criteria 2 — Experience
    experience_years=None,
    current_role=None,
    employment_history=None,   # JSON array [{company,role,from,to,industry}]
    # Criteria 3 — Skills
    skills=None,
    # Criteria 4 — Certifications
    certifications=None,
    # Criteria 5 — Industry
    industry_experience=None,
    # Criteria 6 — Location
    current_city=None,
    current_country=None,
    willing_to_relocate=0,
    work_permit=None,
    # Criteria 7 — Languages
    languages=None,            # comma-sep e.g. "English, French"
    # Criteria 9 — Portfolio
    portfolio_url=None,
    github_url=None,
    # Criteria 10 — Screening
    screening_answers=None,    # JSON array [{id, question, answer}]
    # General
    phone_number=None,
    cover_letter=None,
    cv_file=None,
):
    """Public endpoint — no login required. Validates, deduplicates, then creates Job Applicant."""

    # ── Validation ────────────────────────────────────────────────────────────
    if not job_opening:
        frappe.throw("Job Opening is required")
    if not (applicant_name or "").strip():
        frappe.throw("Full name is required")
    if not email_id or "@" not in email_id:
        frappe.throw("Valid email address is required")

    # Job must be open & published
    job = frappe.db.get_value(
        "Job Opening", job_opening,
        ["name", "job_title", "status", "ec_portal_published", "ec_application_deadline"],
        as_dict=True,
    )
    if not job:
        frappe.throw("Job opening not found")
    if job.status != "Open" or not job.ec_portal_published:
        frappe.throw("This position is no longer accepting applications")
    if job.ec_application_deadline and getdate(job.ec_application_deadline) < getdate(today()):
        frappe.throw("The application deadline has passed")

    # Normalise email
    email_clean = email_id.lower().strip()

    # Duplicate check — same email + same job
    existing = frappe.db.exists("Job Applicant", {
        "job_title": job_opening,
        "email_id":  email_clean,
    })
    if existing:
        frappe.throw("You have already submitted an application for this position with this email address")

    # ── Parse JSON fields ─────────────────────────────────────────────────────
    def _safe_json(val):
        if not val:
            return ""
        if isinstance(val, (list, dict)):
            return json.dumps(val)
        try:
            parsed = json.loads(val)
            return json.dumps(parsed)
        except Exception:
            return str(val)

    # ── Generate tracking token ───────────────────────────────────────────────
    token = uuid.uuid4().hex[:24]

    # ── Create Job Applicant ──────────────────────────────────────────────────
    applicant = frappe.get_doc({
        "doctype":              "Job Applicant",
        "job_title":            job_opening,
        "applicant_name":       applicant_name.strip(),
        "email_id":             email_clean,
        "phone_number":         phone_number or "",
        "status":               "Open",

        # Criteria 1
        "ec_education_level":   education_level or "",
        "ec_field_of_study":    field_of_study or "",
        "ec_university_name":   university_name or "",
        "ec_graduation_year":   int(graduation_year) if graduation_year else None,

        # Criteria 2
        "ec_experience_years":  float(experience_years or 0),
        "ec_current_role":      current_role or "",
        "ec_employment_history":_safe_json(employment_history),

        # Criteria 3
        "ec_skills":            skills or "",

        # Criteria 4
        "ec_certifications":    certifications or "",

        # Criteria 5
        "ec_industry_experience":industry_experience or "",

        # Criteria 6
        "ec_current_city":      current_city or "",
        "ec_current_country":   current_country or "",
        "ec_willing_to_relocate":int(bool(willing_to_relocate)),
        "ec_work_permit":       work_permit or "",

        # Criteria 7
        "ec_languages":         languages or "",

        # Criteria 9
        "ec_portfolio_url":     portfolio_url or "",
        "ec_github_url":        github_url or "",

        # Criteria 10 / General
        "ec_screening_answers": _safe_json(screening_answers),
        "ec_cover_letter":      cover_letter or "",
        "ec_cv_file":           cv_file or "",

        # Meta
        "ec_scoring_status":    "Pending",
        "ec_portal_token":      token,
        "ec_applied_via_portal":1,
    })
    applicant.insert(ignore_permissions=True)
    frappe.db.commit()

    # ── Enqueue scoring (non-blocking) ────────────────────────────────────────
    try:
        frappe.enqueue(
            "ecclesia.api.recruitment_portal_score.score_applicant",
            queue="short",
            job_applicant=applicant.name,
            job_opening=job_opening,
            enqueue_after_commit=True,
        )
    except Exception:
        pass

    return {
        "name":           applicant.name,
        "tracking_token": token,
        "status":         "success",
        "message":        f"Application submitted successfully. Save your tracking token: {token}",
    }