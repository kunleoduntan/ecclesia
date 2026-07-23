"""
ecclesia/api/recruitment_auto_screen.py  (v2 — updated)
=========================================================
Automated Resume Screening Engine — now includes:
  • Grade / Class of degree scoring
  • Location proximity scoring
  • Salary expectation fit scoring
  • Gender diversity equity monitoring (never a penalty, only optional bonus)

SCORING BREAKDOWN (default weights — HR configures per job):
  Education level        15%
  Degree class           5%
  Experience             25%
  Skills match           30%
  Certifications         10%
  Location fit           5%
  Salary fit             10%
  ──────────────────────────
  Total                  100%
  + Gender equity bonus  optional (0–10%)

HOOKS.PY (no change from v1):
  doc_events = {
      "Job Applicant": {
          "after_insert": "ecclesia.api.recruitment_auto_screen.on_job_applicant_submit",
          "on_submit":    "ecclesia.api.recruitment_auto_screen.on_job_applicant_submit",
      }
  }
  scheduler_events = {
      "daily": ["ecclesia.api.recruitment_auto_screen.dispatch_post_closing_emails"]
  }
  after_migrate = ["ecclesia.api.recruitment_custom_fields.create_all"]
"""

import frappe
from frappe import _
from frappe.utils import nowdate, flt, cint, add_days, date_diff, getdate
import json


# ── DEGREE CLASS MAP ──────────────────────────────────────────────────────
# Numeric rank so we can compare minimum vs actual

DEGREE_CLASS_RANK = {
    "first class":          5,
    "second class upper":   4,
    "second class lower":   3,
    "third class":          2,
    "pass":                 1,
    "not applicable":       0,
    "any class":            0,
}

DEGREE_CLASS_SCORE = {
    "first class":          100,
    "second class upper":   80,
    "second class lower":   60,
    "third class":          35,
    "pass":                 20,
    "not applicable":       50,   # non-graduates: neutral
}


# ── EDUCATION LEVEL MAP ───────────────────────────────────────────────────

EDU_RANK = {
    "o-level": 1, "ond": 2, "hnd": 3,
    "bsc": 4, "b.eng": 4, "bsc / b.eng": 4,
    "msc": 5, "mba": 5, "msc / mba": 5,
    "phd": 6,
}


# ── LOCATION SCORE TABLE ──────────────────────────────────────────────────
# How much of the location_weight to award depending on proximity

LOCATION_SCORES = {
    "exact_city":    100,   # same city as job
    "same_state":     65,   # same state, different city
    "different":      25,   # different state
    "remote":        100,   # role allows remote → location irrelevant
    "relocation_yes": 50,   # willing to relocate but not currently in location
}


# ── ENTRY POINTS ──────────────────────────────────────────────────────────

def on_job_applicant_submit(doc, method=None):
    job_opening = doc.job_opening or frappe.db.get_value(
        "Job Opening", {"job_title": doc.job_title}, "name")
    if not job_opening:
        return

    profile_name = frappe.db.get_value(
        "Job Requirement Profile", {"job_opening": job_opening}, "name")
    if not profile_name:
        frappe.db.set_value("Job Applicant", doc.name, {
            "custom_screening_status": "No Profile - Manual Review",
            "custom_screening_score":  0,
        })
        return

    frappe.enqueue(
        "ecclesia.api.recruitment_auto_screen.screen_single_applicant",
        applicant_name=doc.name,
        job_opening=job_opening,
        profile_name=profile_name,
        queue="short",
        timeout=90,
        now=frappe.flags.in_test,
    )


# ── MAIN SCORER ───────────────────────────────────────────────────────────

def screen_single_applicant(applicant_name, job_opening, profile_name):
    try:
        app     = frappe.get_doc("Job Applicant", applicant_name)
        profile = frappe.get_doc("Job Requirement Profile", profile_name)

        result = _score_applicant(app, profile, job_opening)

        # ── Persist result ────────────────────────────────────────────────
        _save_screening_result(app, profile, job_opening, result)

        # ── Update Job Applicant custom fields ────────────────────────────
        status_map = {
            "Shortlisted": "Replied",
            "Rejected":    "Rejected",
            "Refer to HR": "Open",
        }
        frappe.db.set_value("Job Applicant", applicant_name, {
            "custom_screening_status": result["decision"],
            "custom_screening_score":  round(result["total_score"], 1),
            "custom_matched_skills":   ", ".join(result["matched_skills"]),
            "custom_missing_skills":   ", ".join(result["missing_mandatory"]),
            "custom_score_breakdown":  result["breakdown_text"],
            "custom_ai_narrative":     (result["ai_narrative"] or "")[:1000],
            "status": status_map.get(result["decision"], "Open"),
        })

        frappe.db.commit()
        frappe.logger().info(
            f"[Recruit] {app.applicant_name} | {job_opening} | "
            f"Score: {result['total_score']:.1f}% | {result['decision']}"
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(),
            f"Recruitment Screen Error: {applicant_name}")


def _score_applicant(app, profile, job_opening):
    """
    Core scoring function. Returns a dict with all scores and the final decision.
    """
    knockout_failed = False
    knockout_reason = ""

    # ── Pull applicant data ───────────────────────────────────────────────
    education_level  = (app.get("custom_highest_education") or "").lower().strip()
    degree_class_raw = (app.get("custom_degree_class") or "not applicable").lower().strip()
    years_exp        = flt(app.get("custom_years_experience") or 0)
    skills_text      = app.get("custom_skills") or ""
    certifications   = app.get("custom_certifications") or ""
    current_city     = (app.get("custom_current_city") or "").lower().strip()
    current_state    = (app.get("custom_current_state") or "").lower().strip()
    open_to_reloc    = (app.get("custom_open_to_relocation") or "No").lower()
    work_mode_pref   = (app.get("custom_work_mode_preference") or "").lower()
    salary_exp_min   = flt(app.get("custom_salary_expectation_min") or 0)
    salary_exp_max   = flt(app.get("custom_salary_expectation_max") or 0)
    gender           = (app.get("custom_gender") or "").lower().strip()
    cover_letter     = app.get("custom_cover_letter") or ""

    # ── Required skills from profile ──────────────────────────────────────
    req_skills = frappe.get_all("Job Requirement Skill",
        filters={"parent": profile.name},
        fields=["skill", "is_mandatory", "weight"])

    mandatory_skills     = [s.skill.lower() for s in req_skills if s.get("is_mandatory")]
    all_req_skills       = req_skills
    app_skills_lower     = [s.strip().lower() for s in skills_text.split(",") if s.strip()]

    # ── 1. EDUCATION LEVEL SCORE ──────────────────────────────────────────
    min_edu_key   = (profile.min_education or "").lower().replace(" / ","/").replace(" ","").replace(".","")
    required_rank = EDU_RANK.get(min_edu_key, 0)

    # Try multiple key variants to match the applicant's selection
    actual_key    = education_level.replace(" / ","/").replace(" ","").replace(".","")
    actual_rank   = EDU_RANK.get(actual_key, 0)
    if actual_rank == 0:  # fallback: partial match
        for k, v in EDU_RANK.items():
            if k in education_level or education_level in k:
                actual_rank = v
                break

    if actual_rank >= required_rank and required_rank > 0:
        education_score = 80 + min(20, (actual_rank - required_rank) * 10)
    elif required_rank == 0:
        education_score = 70  # no requirement set
    else:
        education_score = max(0, (actual_rank / max(1, required_rank)) * 80)

    # ── 2. DEGREE CLASS SCORE (NEW) ───────────────────────────────────────
    min_class_key    = (profile.min_degree_class or "any class").lower().strip()
    pref_class_key   = (profile.preferred_degree_class or "").lower().strip()

    actual_class_rank  = DEGREE_CLASS_RANK.get(degree_class_raw, 0)
    required_class_rank = DEGREE_CLASS_RANK.get(min_class_key, 0)

    # Raw degree class score
    degree_class_score = DEGREE_CLASS_SCORE.get(degree_class_raw, 50)

    # Knockout check
    if (cint(profile.degree_class_knockout)
            and required_class_rank > 0
            and actual_class_rank < required_class_rank
            and degree_class_raw not in ("not applicable",)):
        knockout_failed = True
        knockout_reason = (f"Degree class ({app.get('custom_degree_class')}) "
                           f"is below the minimum required ({profile.min_degree_class})")

    # Bonus for being at or above preferred class
    if pref_class_key and actual_class_rank >= DEGREE_CLASS_RANK.get(pref_class_key, 0) > 0:
        degree_class_score = min(100, degree_class_score + 15)

    # ── 3. EXPERIENCE SCORE ───────────────────────────────────────────────
    min_exp = flt(profile.min_experience_years)
    max_exp = flt(profile.max_experience_years) or (min_exp + 10)

    if years_exp >= min_exp:
        experience_score = min(100, 60 + (years_exp - min_exp) / max(1, max_exp - min_exp) * 40)
    else:
        experience_score = max(0, (years_exp / max(1, min_exp)) * 60)

    # ── 4. SKILLS MATCH SCORE ─────────────────────────────────────────────
    matched_skills   = []
    missing_mandatory = []

    for req_skill in all_req_skills:
        skill_lower = req_skill.skill.lower()
        found = any(skill_lower in sk or sk in skill_lower for sk in app_skills_lower)
        if found:
            matched_skills.append(req_skill.skill)
        elif req_skill.get("is_mandatory"):
            missing_mandatory.append(req_skill.skill)

    if missing_mandatory:
        knockout_failed = True
        knockout_reason = f"Missing mandatory skills: {', '.join(missing_mandatory)}"

    skills_score = (len(matched_skills) / max(1, len(all_req_skills))) * 100

    # ── 5. CERTIFICATIONS SCORE ───────────────────────────────────────────
    req_certs = [c.strip().lower() for c in (profile.required_certifications or "").split(",") if c.strip()]
    app_certs = [c.strip().lower() for c in certifications.split(",") if c.strip()]

    if req_certs:
        cert_matches = sum(1 for rc in req_certs
                          if any(rc in ac or ac in rc for ac in app_certs))
        certifications_score = (cert_matches / len(req_certs)) * 100
    else:
        certifications_score = 100  # no certs required → full marks

    # ── 6. LOCATION SCORE (NEW) ───────────────────────────────────────────
    location_score = _compute_location_score(
        profile=profile,
        current_city=current_city,
        current_state=current_state,
        open_to_reloc=open_to_reloc,
        work_mode_pref=work_mode_pref,
    )

    # ── 7. SALARY FIT SCORE (NEW) ─────────────────────────────────────────
    salary_score, salary_knockout = _compute_salary_score(
        profile=profile,
        salary_exp_min=salary_exp_min,
        salary_exp_max=salary_exp_max,
    )

    if salary_knockout:
        knockout_failed = True
        knockout_reason = (f"Salary expectation (₦{salary_exp_min:,.0f}–₦{salary_exp_max:,.0f}) "
                           f"exceeds budget (max ₦{flt(profile.salary_budget_max):,.0f})")

    # ── WEIGHTED TOTAL ────────────────────────────────────────────────────
    ew  = flt(profile.education_weight) / 100
    dcw = flt(profile.degree_class_weight) / 100
    xw  = flt(profile.experience_weight) / 100
    sw  = flt(profile.skills_weight) / 100
    cw  = flt(profile.certifications_weight) / 100
    lw  = flt(profile.location_weight) / 100
    saw = flt(profile.salary_weight) / 100

    tw = ew + dcw + xw + sw + cw + lw + saw or 1  # guard against zero

    total_score = (
        education_score      * ew  +
        degree_class_score   * dcw +
        experience_score     * xw  +
        skills_score         * sw  +
        certifications_score * cw  +
        location_score       * lw  +
        salary_score         * saw
    ) / tw

    # ── 8. GENDER EQUITY BONUS (NEW) ─────────────────────────────────────
    # Applied AFTER the main score. Never penalises; only adds a small bonus
    # when the shortlisted pool for this job is imbalanced.
    gender_bonus = 0.0
    gender_note  = ""

    if cint(profile.gender_target_enabled) and profile.gender_target and gender:
        gender_bonus, gender_note = _compute_gender_equity_bonus(
            job_opening=job_opening,
            profile=profile,
            applicant_gender=gender,
        )
        total_score = min(100, total_score + gender_bonus)

    # ── AUTO DECISION ─────────────────────────────────────────────────────
    tsl = flt(profile.auto_shortlist_threshold) or 70
    tar = flt(profile.auto_reject_threshold) or 40

    if knockout_failed:
        decision = "Rejected"
    elif total_score >= tsl:
        decision = "Shortlisted"
    elif total_score < tar:
        decision = "Rejected"
    else:
        decision = "Refer to HR"

    # ── SCORE BREAKDOWN TEXT ──────────────────────────────────────────────
    breakdown_text = (
        f"Education: {education_score:.0f}% | "
        f"Degree Class: {degree_class_score:.0f}% | "
        f"Experience: {experience_score:.0f}% | "
        f"Skills: {skills_score:.0f}% | "
        f"Certs: {certifications_score:.0f}% | "
        f"Location: {location_score:.0f}% | "
        f"Salary: {salary_score:.0f}%"
    )
    if gender_bonus > 0:
        breakdown_text += f" | Equity Bonus: +{gender_bonus:.1f}%"

    # ── AI NARRATIVE ──────────────────────────────────────────────────────
    ai_narrative = _generate_ai_narrative(
        app=app,
        profile=profile,
        total_score=total_score,
        decision=decision,
        matched_skills=matched_skills,
        missing_mandatory=missing_mandatory,
        knockout_failed=knockout_failed,
        knockout_reason=knockout_reason,
        degree_class_raw=degree_class_raw,
        location_score=location_score,
        salary_score=salary_score,
        gender_note=gender_note,
    )

    return {
        "total_score":        total_score,
        "education_score":    education_score,
        "degree_class_score": degree_class_score,
        "experience_score":   experience_score,
        "skills_score":       skills_score,
        "certifications_score": certifications_score,
        "location_score":     location_score,
        "salary_score":       salary_score,
        "gender_bonus":       gender_bonus,
        "matched_skills":     matched_skills,
        "missing_mandatory":  missing_mandatory,
        "knockout_failed":    knockout_failed,
        "knockout_reason":    knockout_reason,
        "decision":           decision,
        "breakdown_text":     breakdown_text,
        "ai_narrative":       ai_narrative,
    }


# ── LOCATION SCORER ───────────────────────────────────────────────────────

def _compute_location_score(profile, current_city, current_state,
                             open_to_reloc, work_mode_pref):
    """
    Scores how well the applicant's location matches the job location.
    Remote roles score full marks regardless of location.
    """
    # Role allows remote → location is irrelevant
    if cint(profile.remote_allowed) or "remote" in work_mode_pref:
        return LOCATION_SCORES["remote"]

    # No location requirement set → neutral score
    requirement = (profile.location_requirement or "Any Location")
    if requirement == "Any Location":
        return 80  # slight deduction for any-location roles still — proximity matters

    job_city  = (profile.job_location_city  or "").lower().strip()
    job_state = (profile.job_location_state or "").lower().strip()

    # Exact city match
    if job_city and current_city and (
        job_city in current_city or current_city in job_city
    ):
        return LOCATION_SCORES["exact_city"]

    # Same state
    if job_state and current_state and (
        job_state in current_state or current_state in job_state
    ):
        if requirement in ("Same State", "Any Location"):
            return LOCATION_SCORES["same_state"]
        elif requirement == "Specified City Only":
            return 30  # state match but city required
        return LOCATION_SCORES["same_state"]

    # Different location but willing to relocate
    if "yes" in open_to_reloc:
        if cint(profile.relocation_supported):
            return LOCATION_SCORES["relocation_yes"] + 15  # company supports reloc
        return LOCATION_SCORES["relocation_yes"]

    # Different location, not willing to relocate
    if requirement == "Specified City Only":
        return 10   # hard miss
    return LOCATION_SCORES["different"]


# ── SALARY SCORER ─────────────────────────────────────────────────────────

def _compute_salary_score(profile, salary_exp_min, salary_exp_max):
    """
    Scores how well the applicant's salary expectation fits the budget.

    Returns (score, knockout_triggered).
    Full marks if:  expectation_max <= budget_max  AND  expectation_min >= budget_min × 0.7
    Partial marks if expectation is close but slightly above
    Zero / knockout if far above budget
    """
    budget_min = flt(profile.salary_budget_min)
    budget_max = flt(profile.salary_budget_max)
    knockout   = cint(profile.salary_knockout)

    # No salary requirement configured → full marks
    if budget_max == 0:
        return 100, False

    # Applicant didn't state salary expectation → neutral
    if salary_exp_min == 0 and salary_exp_max == 0:
        return 70, False   # slight uncertainty — refer to HR

    # Use the max expectation as the primary comparison figure
    # If applicant only stated min, use min × 1.1 as estimate of max
    effective_exp = salary_exp_max if salary_exp_max > 0 else salary_exp_min * 1.1

    # Expectation is within budget → full marks
    if effective_exp <= budget_max:
        # Extra points if expectation is also above budget_min (not underpriced)
        if salary_exp_min >= budget_min * 0.7:
            return 100, False
        return 85, False   # slightly underpriced — might leave quickly

    # Expectation is over budget
    overshoot_pct = ((effective_exp - budget_max) / budget_max) * 100

    if overshoot_pct <= 10:
        # Within 10% over → still worth interviewing, refer to HR
        return 55, False
    elif overshoot_pct <= 25:
        # 10–25% over → possible with negotiation
        return 30, False
    else:
        # More than 25% over budget
        if knockout:
            return 0, True   # auto-reject
        return 10, False     # very low score but no hard knockout


# ── GENDER EQUITY BONUS ───────────────────────────────────────────────────

def _compute_gender_equity_bonus(job_opening, profile, applicant_gender):
    """
    Checks the current gender composition of shortlisted candidates for this job.
    If the target gender is underrepresented (< 30% of shortlisted),
    eligible candidates receive the configured equity bonus.

    This NEVER penalises any gender. It only adds a small bonus to help
    achieve balance in the shortlisted pool.
    """
    target_gender = (profile.gender_target or "").lower().strip()
    bonus_pct     = flt(profile.gender_equity_bonus) or 5.0

    # Only apply if this applicant is the target gender
    if target_gender not in applicant_gender and applicant_gender not in target_gender:
        return 0.0, ""

    # Count gender distribution in already-shortlisted candidates for this job
    results = frappe.db.sql("""
        SELECT ja.custom_gender, COUNT(*) AS cnt
        FROM `tabJob Applicant` ja
        WHERE ja.job_opening = %s
          AND ja.custom_screening_status = 'Shortlisted'
          AND ja.custom_gender IS NOT NULL
          AND ja.custom_gender != ''
        GROUP BY ja.custom_gender
    """, job_opening, as_dict=True)

    total_shortlisted = sum(r.cnt for r in results)
    if total_shortlisted < 3:
        # Pool too small to assess — don't apply bonus yet
        return 0.0, ""

    target_count = sum(r.cnt for r in results
                       if target_gender in (r.custom_gender or "").lower())
    target_pct   = (target_count / total_shortlisted) * 100

    if target_pct < 30:
        note = (f"Equity bonus applied: {target_gender.title()} candidates are "
                f"{target_pct:.0f}% of shortlisted pool (target: 30%+).")
        return bonus_pct, note

    return 0.0, ""


# ── AI NARRATIVE GENERATOR ────────────────────────────────────────────────

def _generate_ai_narrative(app, profile, total_score, decision,
                            matched_skills, missing_mandatory,
                            knockout_failed, knockout_reason,
                            degree_class_raw, location_score,
                            salary_score, gender_note):
    """
    Calls Claude to write a 3-4 sentence recruiter-quality screening summary.
    Covers degree class, location, salary, and skills observations.
    Falls back to a rule-based summary if API is unavailable.
    """
    try:
        import requests

        prompt = (
            "You are a professional HR recruiter. Write a concise 3–4 sentence "
            "screening summary for the recruiter's file. Be factual, neutral, and professional.\n\n"
            f"Position: {profile.job_opening}\n"
            f"Candidate: {app.applicant_name}\n"
            f"Total Score: {total_score:.1f}%  |  Decision: {decision}\n"
            f"Education: {app.get('custom_highest_education','Not stated')} — "
            f"Class: {app.get('custom_degree_class','Not stated')}\n"
            f"Experience: {app.get('custom_years_experience','0')} years\n"
            f"Matched Skills: {', '.join(matched_skills) or 'None'}\n"
            f"Missing Mandatory Skills: {', '.join(missing_mandatory) or 'None'}\n"
            f"Knockout Triggered: {knockout_failed}"
            + (f" — Reason: {knockout_reason}" if knockout_failed else "") + "\n"
            f"Location Score: {location_score:.0f}%\n"
            f"Salary Fit Score: {salary_score:.0f}%\n"
            + (f"Diversity Note: {gender_note}\n" if gender_note else "") +
            "\nWrite in third person. No markdown, no bullet points — just plain sentences. "
            "Mention degree class, location fit, and salary fit if they significantly impacted the score."
        )

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 250,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )
        if resp.ok:
            text = resp.json().get("content", [{}])[0].get("text", "")
            if text:
                return text.strip()
    except Exception:
        pass  # fall through to rule-based

    # ── Rule-based fallback ───────────────────────────────────────────────
    name  = app.applicant_name
    edu   = app.get("custom_highest_education") or "unspecified education"
    cls   = app.get("custom_degree_class") or "unspecified class"
    exp   = app.get("custom_years_experience") or 0

    if knockout_failed:
        return (
            f"{name} was automatically rejected due to: {knockout_reason}. "
            f"Their application should not proceed to interview without HR review."
        )
    elif total_score >= 70:
        loc_note = "" if location_score >= 70 else f" Location proximity scored {location_score:.0f}%."
        sal_note = "" if salary_score >= 70 else f" Salary expectations may require discussion."
        return (
            f"{name} scored {total_score:.1f}% and meets the shortlisting threshold. "
            f"They hold a {cls} {edu} with {exp} years of experience. "
            f"Matched skills: {', '.join(matched_skills[:4]) or 'profile match'}."
            f"{loc_note}{sal_note}"
        )
    else:
        return (
            f"{name} scored {total_score:.1f}%, below the shortlisting threshold. "
            f"Profile: {cls} {edu}, {exp} years experience. "
            f"{'Missing mandatory skills: ' + ', '.join(missing_mandatory[:3]) + '.' if missing_mandatory else 'Skill match was partial.'}"
        )


# ── SAVE RESULT ───────────────────────────────────────────────────────────

def _save_screening_result(app, profile, job_opening, result):
    """Creates or updates a Resume Screening Result record."""
    existing = frappe.db.get_value(
        "Resume Screening Result",
        {"job_opening": job_opening, "candidate_name": app.applicant_name},
        "name"
    )

    if existing:
        doc = frappe.get_doc("Resume Screening Result", existing)
    else:
        doc = frappe.new_doc("Resume Screening Result")
        resume_name = frappe.db.get_value("Resume",
            {"job_applicant": app.name}, "name")
        if resume_name:
            doc.resume = resume_name
        doc.job_opening = job_opening

    doc.candidate_name           = app.applicant_name
    doc.screening_date           = nowdate()
    doc.education_score          = round(result["education_score"], 1)
    doc.experience_score         = round(result["experience_score"], 1)
    doc.skills_score             = round(result["skills_score"], 1)
    doc.certifications_score     = round(result["certifications_score"], 1)
    doc.total_score              = round(result["total_score"], 1)
    doc.matched_skills           = ", ".join(result["matched_skills"])
    doc.missing_mandatory_skills = ", ".join(result["missing_mandatory"])
    doc.knockout_failed          = cint(result["knockout_failed"])
    doc.auto_decision            = result["decision"]
    doc.ai_narrative             = result["ai_narrative"] or ""
    doc.save(ignore_permissions=True)
    frappe.db.commit()


# ── SCHEDULER: EMAIL DISPATCH (unchanged from v1) ─────────────────────────

def dispatch_post_closing_emails():
    """
    Runs daily. Finds Job Openings past closing date and dispatches emails.
    """
    today     = getdate(nowdate())
    yesterday = add_days(today, -1)

    due_openings = frappe.db.sql("""
        SELECT name, job_title, closes_on, company,
               IFNULL(custom_emails_dispatched, 0) AS emails_dispatched
        FROM `tabJob Opening`
        WHERE closes_on IN (%s, %s)
          AND status != 'Cancelled'
          AND (custom_emails_dispatched IS NULL OR custom_emails_dispatched = 0)
    """, (str(today), str(yesterday)), as_dict=True)

    for opening in due_openings:
        try:
            _dispatch_emails_for_opening(opening)
            frappe.db.set_value("Job Opening", opening.name,
                "custom_emails_dispatched", 1)
            frappe.db.commit()
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                f"Recruitment Email Dispatch Error: {opening.name}")


def _dispatch_emails_for_opening(opening):
    job_opening = opening.name
    results = frappe.get_all(
        "Resume Screening Result",
        filters={"job_opening": job_opening},
        fields=["name","candidate_name","total_score","auto_decision",
                "hr_override","matched_skills","ai_narrative"]
    )

    shortlisted, rejected, referred = [], [], []
    for r in results:
        decision = r.hr_override or r.auto_decision
        if decision == "Shortlisted":
            shortlisted.append(r)
        elif decision == "Rejected":
            rejected.append(r)
        else:
            referred.append(r)

    for r in shortlisted:
        email = _get_applicant_email(r.candidate_name, job_opening)
        if email:
            _send_shortlist_email(email, r.candidate_name, opening.job_title,
                                  opening.company, r.total_score, r.matched_skills)

    send_rejections = frappe.db.get_value("Job Opening", job_opening,
        "custom_send_rejection_email") or 1
    if cint(send_rejections):
        for r in rejected:
            email = _get_applicant_email(r.candidate_name, job_opening)
            if email:
                _send_rejection_email(email, r.candidate_name,
                                      opening.job_title, opening.company)

    _notify_hr_summary(opening, shortlisted, rejected, referred)


def _get_applicant_email(candidate_name, job_opening):
    return frappe.db.get_value(
        "Job Applicant",
        {"applicant_name": candidate_name, "job_opening": job_opening},
        "email_id"
    )


# ── EMAIL TEMPLATES ───────────────────────────────────────────────────────

def _send_shortlist_email(to_email, candidate_name, job_title,
                           company, score, matched_skills):
    first = candidate_name.split()[0] if candidate_name else "Applicant"
    matched = matched_skills or "Your profile matched our requirements"
    subject = f"Congratulations! You've been shortlisted — {job_title} at {company}"

    html = f"""
<div style="font-family:Calibri,Arial,sans-serif;max-width:600px;margin:0 auto;
            background:#fff;border-radius:8px;border:1px solid #e5e7eb;overflow:hidden">
  <div style="background:linear-gradient(135deg,#312E81,#7C3AED);padding:32px 36px;text-align:center">
    <div style="font-size:38px;margin-bottom:8px">🎉</div>
    <h1 style="color:#fff;font-size:22px;margin:0;font-weight:800">Congratulations, {first}!</h1>
    <p style="color:rgba(255,255,255,.8);font-size:14px;margin:8px 0 0">You have been shortlisted.</p>
  </div>
  <div style="padding:32px 36px">
    <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 18px">
      Dear <strong>{candidate_name}</strong>,
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 18px">
      Following a review of your application, you have been
      <strong style="color:#059669">shortlisted</strong> for
      <strong>{job_title}</strong> at <strong>{company}</strong>.
    </p>
    <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;
                padding:18px 22px;margin-bottom:22px;text-align:center">
      <div style="font-size:18px;font-weight:800;color:#065F46">{job_title}</div>
      <div style="font-size:13px;color:#6B7280;margin-top:3px">{company}</div>
      <div style="margin-top:10px;display:inline-block;background:#DCFCE7;color:#166534;
                  font-size:12px;font-weight:700;padding:4px 14px;border-radius:99px">
        Screening Score: {score:.1f}%
      </div>
    </div>
    <p style="color:#374151;font-size:14px;margin:0 0 6px"><strong>Skills matched:</strong></p>
    <p style="color:#4B5563;font-size:14px;font-style:italic;background:#F9FAFB;
              padding:10px 14px;border-radius:6px;border-left:3px solid #7C3AED;margin:0 0 22px">
      {matched}
    </p>
    <div style="background:#EDE9FE;border-radius:10px;padding:18px 22px;margin-bottom:22px">
      <p style="font-weight:700;color:#5B21B6;margin:0 0 8px">📋 Next Steps</p>
      <ol style="color:#374151;font-size:14px;line-height:1.9;margin:0;padding-left:20px">
        <li>Our HR team will contact you within <strong>3–5 business days</strong> to schedule your interview.</li>
        <li>Please ensure your contact details are up to date.</li>
        <li>Prepare to discuss your experience relevant to the skills above.</li>
      </ol>
    </div>
    <p style="color:#374151;font-size:14px;margin:0">
      We look forward to meeting you.<br><br>
      Warm regards,<br><strong>HR &amp; Talent Acquisition</strong><br><em>{company}</em>
    </p>
  </div>
  <div style="background:#F9FAFB;padding:14px 36px;text-align:center;border-top:1px solid #E5E7EB">
    <p style="color:#9CA3AF;font-size:11px;margin:0">
      This is an automated notification. Powered by Ecclesia HR · Value Impacts Consulting.
    </p>
  </div>
</div>"""
    frappe.sendmail(recipients=[to_email], subject=subject, message=html, now=False)


def _send_rejection_email(to_email, candidate_name, job_title, company):
    first = candidate_name.split()[0] if candidate_name else "Applicant"
    subject = f"Update on Your Application — {job_title} at {company}"

    html = f"""
<div style="font-family:Calibri,Arial,sans-serif;max-width:600px;margin:0 auto;
            background:#fff;border-radius:8px;border:1px solid #e5e7eb;overflow:hidden">
  <div style="background:linear-gradient(135deg,#1F2937,#374151);padding:30px 36px;text-align:center">
    <div style="font-size:36px;margin-bottom:8px">📬</div>
    <h1 style="color:#fff;font-size:20px;margin:0;font-weight:700">Thank You for Applying</h1>
  </div>
  <div style="padding:32px 36px">
    <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 18px">
      Dear <strong>{candidate_name}</strong>,
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 18px">
      Thank you for applying for <strong>{job_title}</strong> at <strong>{company}</strong>.
      After a careful review of all applications, we regret to inform you that
      your application was not successful on this occasion.
    </p>
    <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;
                padding:18px 22px;margin-bottom:22px">
      <p style="font-weight:700;color:#92400E;margin:0 0 8px">💡 We Encourage You To</p>
      <ul style="color:#374151;font-size:14px;line-height:1.9;margin:0;padding-left:20px">
        <li>Continue developing your skills and professional certifications</li>
        <li>Watch for future openings that better match your profile</li>
        <li>Keep your resume updated for upcoming opportunities</li>
      </ul>
    </div>
    <p style="color:#374151;font-size:14px;margin:0">
      We appreciate your interest in {company} and wish you every success.<br><br>
      Kind regards,<br><strong>HR &amp; Talent Acquisition</strong><br><em>{company}</em>
    </p>
  </div>
  <div style="background:#F9FAFB;padding:14px 36px;text-align:center;border-top:1px solid #E5E7EB">
    <p style="color:#9CA3AF;font-size:11px;margin:0">
      Powered by Ecclesia HR · Value Impacts Consulting.
    </p>
  </div>
</div>"""
    frappe.sendmail(recipients=[to_email], subject=subject, message=html, now=False)


def _notify_hr_summary(opening, shortlisted, rejected, referred):
    hr_users = frappe.get_all("Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"], limit=10)
    hr_emails = [frappe.db.get_value("User", u.parent, "email")
                 for u in hr_users
                 if frappe.db.get_value("User", u.parent, "email")]
    if not hr_emails:
        return

    def rows(results, color, verdict):
        if not results:
            return '<tr><td colspan="3" style="padding:10px;color:#9CA3AF;text-align:center">None</td></tr>'
        return "".join(
            f'<tr><td style="padding:8px 12px;border-bottom:1px solid #F3F4F6">{r.candidate_name}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #F3F4F6">{flt(r.total_score):.1f}%</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #F3F4F6">'
            f'<span style="background:{color};color:#fff;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700">{verdict}</span>'
            f'</td></tr>'
            for r in results
        )

    html = f"""
<div style="font-family:Calibri,Arial,sans-serif;max-width:700px;margin:0 auto;
            border:1px solid #E5E7EB;border-radius:8px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#312E81,#7C3AED);padding:26px 36px">
    <h2 style="color:#fff;margin:0;font-size:20px">📊 Recruitment Screening Summary</h2>
    <p style="color:rgba(255,255,255,.75);margin:5px 0 0;font-size:14px">
      {opening.job_title} · {opening.company} · Closing date: {opening.closes_on}
    </p>
  </div>
  <div style="padding:26px 36px">
    <div style="display:flex;gap:14px;margin-bottom:22px">
      <div style="flex:1;background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:28px;font-weight:900;color:#059669">{len(shortlisted)}</div>
        <div style="font-size:12px;color:#6B7280;margin-top:3px">Shortlisted</div>
      </div>
      <div style="flex:1;background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:28px;font-weight:900;color:#D97706">{len(referred)}</div>
        <div style="font-size:12px;color:#6B7280;margin-top:3px">Refer to HR</div>
      </div>
      <div style="flex:1;background:#FEE2E2;border:1px solid #FECACA;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:28px;font-weight:900;color:#DC2626">{len(rejected)}</div>
        <div style="font-size:12px;color:#6B7280;margin-top:3px">Rejected</div>
      </div>
    </div>
    <h3 style="font-size:14px;font-weight:700;color:#111;margin:0 0 8px">✅ Shortlisted Candidates</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px">
      <thead style="background:#F9FAFB">
        <tr>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6B7280;text-transform:uppercase">Candidate</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6B7280;text-transform:uppercase">Score</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6B7280;text-transform:uppercase">Decision</th>
        </tr>
      </thead>
      <tbody>{rows(shortlisted,'#059669','Shortlisted')}</tbody>
    </table>
    <h3 style="font-size:14px;font-weight:700;color:#111;margin:0 0 8px">🔍 Referred — Manual Review Needed</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px">
      <thead style="background:#F9FAFB">
        <tr>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6B7280;text-transform:uppercase">Candidate</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6B7280;text-transform:uppercase">Score</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6B7280;text-transform:uppercase">Decision</th>
        </tr>
      </thead>
      <tbody>{rows(referred,'#D97706','Refer to HR')}</tbody>
    </table>
    <p style="color:#6B7280;font-size:12px;margin:0">
      Shortlisted candidates have been emailed. Log in to ERPNext to review borderline candidates.
    </p>
  </div>
</div>"""

    frappe.sendmail(
        recipients=hr_emails,
        subject=f"[Recruitment] {opening.job_title} — {len(shortlisted)} Shortlisted, {len(referred)} Need Review",
        message=html,
        now=False,
    )


# ── HR MANAGEMENT ENDPOINTS ───────────────────────────────────────────────

@frappe.whitelist()
def rescreen_all_applicants(job_opening):
    """Re-run screening for all applicants — useful after profile changes."""
    frappe.only_for("HR Manager")
    profile_name = frappe.db.get_value(
        "Job Requirement Profile", {"job_opening": job_opening}, "name")
    if not profile_name:
        frappe.throw(_(f"No Job Requirement Profile found for {job_opening}"))
    applicants = frappe.get_all("Job Applicant",
        filters={"job_opening": job_opening}, fields=["name"])
    for a in applicants:
        frappe.enqueue(
            "ecclesia.api.recruitment_auto_screen.screen_single_applicant",
            applicant_name=a.name,
            job_opening=job_opening,
            profile_name=profile_name,
            queue="short", timeout=90,
        )
    return {"enqueued": len(applicants)}


@frappe.whitelist()
def manually_dispatch_emails(job_opening):
    """Trigger email dispatch without waiting for the nightly scheduler."""
    frappe.only_for("HR Manager")
    opening = frappe.db.get_value("Job Opening", job_opening,
        ["name","job_title","company","closes_on"], as_dict=True)
    if not opening:
        frappe.throw(_(f"Job Opening {job_opening} not found"))
    _dispatch_emails_for_opening(opening)
    frappe.db.set_value("Job Opening", job_opening, "custom_emails_dispatched", 1)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def get_screening_dashboard(job_opening):
    """Returns stats and full ranked candidate list for the HR dashboard."""
    frappe.only_for("HR Manager")
    results = frappe.get_all("Resume Screening Result",
        filters={"job_opening": job_opening},
        fields=["name","candidate_name","total_score","auto_decision",
                "hr_override","matched_skills","missing_mandatory_skills",
                "knockout_failed","ai_narrative","screening_date"],
        order_by="total_score desc")
    stats = {
        "total":       len(results),
        "shortlisted": sum(1 for r in results if (r.hr_override or r.auto_decision)=="Shortlisted"),
        "rejected":    sum(1 for r in results if (r.hr_override or r.auto_decision)=="Rejected"),
        "referred":    sum(1 for r in results if (r.hr_override or r.auto_decision)=="Refer to HR"),
        "avg_score":   round(sum(flt(r.total_score) for r in results) / max(1,len(results)), 1),
    }
    opening = frappe.db.get_value("Job Opening", job_opening,
        ["name","job_title","company","closes_on","status",
         "custom_emails_dispatched"], as_dict=True) or {}
    return {
        "opening":  {k: str(v) if hasattr(v,"isoformat") else v for k,v in opening.items()},
        "stats":    stats,
        "results":  results,
    }


@frappe.whitelist()
def override_decision(result_name, new_decision, notes=None):
    """HR manually overrides an auto-decision."""
    frappe.only_for("HR Manager")
    frappe.db.set_value("Resume Screening Result", result_name, {
        "hr_override": new_decision,
        "hr_notes":    notes or "",
    })
    frappe.db.commit()
    return {"success": True}