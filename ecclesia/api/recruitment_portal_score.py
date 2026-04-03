# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/api/recruitment_portal_score.py
#
# 10-Criteria Scoring Engine
# ─────────────────────────────────────────────────────────────
# 1.  Education Level          (weight: ec_weight_education)
# 2.  Years of Experience      (weight: ec_weight_experience)
# 3.  Required + Nice-to-Have Skills (weight: ec_weight_skills)
# 4.  Certifications           (weight: ec_weight_certifications)
# 5.  Industry Experience      (weight: ec_weight_industry)
# 6.  Location / Eligibility   (weight: ec_weight_location)
# 7.  Language Skills          (weight: ec_weight_languages)
# 8.  Employment Stability     (weight: ec_weight_stability)
# 9.  Portfolio / Projects     (weight: ec_weight_portfolio)
# 10. Screening Q&A            (weight: ec_weight_screening)
#
# Pre-scoring:
#   - Knock-out questions (auto-reject if failed)
#   - Duplicate detection
# ─────────────────────────────────────────────────────────────

import frappe
import json
import re
from datetime import datetime
from frappe.utils import flt, cint, today


# ── Education hierarchy ───────────────────────────────────────────────────────
EDUCATION_RANK = {
    "":                     0,
    "High School":          1,
    "OND / NCE":            2,
    "HND":                  3,
    "Bachelor's Degree":    4,
    "Postgraduate Diploma": 5,
    "Master's Degree":      6,
    "Doctorate / PhD":      7,
}


# ═════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINTS
# ═════════════════════════════════════════════════════════════════════════════

def score_applicant(job_applicant: str, job_opening: str):
    """
    Main scoring pipeline. Called by enqueue after application submit.
    Steps:
      1. Duplicate detection
      2. Knock-out questions
      3. 10-criteria weighted scoring
      4. Auto-reject if below threshold
      5. Save all results to Job Applicant
    """
    try:
        app = frappe.get_doc("Job Applicant", job_applicant)
        job = _get_job(job_opening)

        if not job:
            frappe.db.set_value("Job Applicant", job_applicant, "ec_scoring_status", "Scored")
            return

        # Step 1 — Duplicate detection ─────────────────────────────────────
        dup = _check_duplicate(app, job_opening)
        if dup:
            frappe.db.set_value("Job Applicant", job_applicant, {
                "ec_is_duplicate":    1,
                "ec_duplicate_of":    dup,
                "ec_scoring_status":  "Duplicate",
                "ec_total_score":     0,
            })
            frappe.db.commit()
            return

        # Step 2 — Knock-out questions ──────────────────────────────────────
        ko_result = _check_knockout(app, job)
        if not ko_result["passed"]:
            frappe.db.set_value("Job Applicant", job_applicant, {
                "ec_knockout_passed":       0,
                "ec_knockout_failed_reason":ko_result["reason"],
                "ec_scoring_status":        "Knocked Out",
                "ec_total_score":           0,
            })
            # Auto-update status to Rejected
            frappe.db.set_value("Job Applicant", job_applicant, "status", "Rejected")
            frappe.db.commit()
            try:
                _notify_knockout(app, ko_result["reason"])
            except Exception:
                pass
            return

        frappe.db.set_value("Job Applicant", job_applicant, {
            "ec_knockout_passed": 1,
            "ec_knockout_failed_reason": "",
        })

        # Step 3 — Compute avg job duration ────────────────────────────────
        avg_duration = _compute_avg_duration(app)
        if avg_duration > 0:
            frappe.db.set_value("Job Applicant", job_applicant, "ec_avg_job_duration", avg_duration)

        # Step 4 — 10-criteria scoring ──────────────────────────────────────
        if not cint(job.get("ec_scoring_enabled", 1)):
            frappe.db.set_value("Job Applicant", job_applicant, "ec_scoring_status", "Scored")
            return

        weights = _normalize_weights(job)
        breakdown = {}
        total = 0.0

        # ── Criterion 1: Education ─────────────────────────────────────────
        c1 = _score_education(app, job, weights["education"])
        breakdown["education"] = c1
        total += c1["earned"]

        # ── Criterion 2: Experience ────────────────────────────────────────
        c2 = _score_experience(app, job, weights["experience"])
        breakdown["experience"] = c2
        total += c2["earned"]

        # ── Criterion 3: Skills ────────────────────────────────────────────
        c3 = _score_skills(app, job, weights["skills"])
        breakdown["skills"] = c3
        total += c3["earned"]

        # ── Criterion 4: Certifications ────────────────────────────────────
        c4 = _score_certifications(app, job, weights["certifications"])
        breakdown["certifications"] = c4
        total += c4["earned"]

        # ── Criterion 5: Industry ──────────────────────────────────────────
        c5 = _score_industry(app, job, weights["industry"])
        breakdown["industry"] = c5
        total += c5["earned"]

        # ── Criterion 6: Location ──────────────────────────────────────────
        c6 = _score_location(app, job, weights["location"])
        breakdown["location"] = c6
        total += c6["earned"]

        # ── Criterion 7: Languages ─────────────────────────────────────────
        c7 = _score_languages(app, job, weights["languages"])
        breakdown["languages"] = c7
        total += c7["earned"]

        # ── Criterion 8: Employment Stability ─────────────────────────────
        c8 = _score_stability(app, job, weights["stability"], avg_duration)
        breakdown["stability"] = c8
        total += c8["earned"]

        # ── Criterion 9: Portfolio ─────────────────────────────────────────
        c9 = _score_portfolio(app, job, weights["portfolio"])
        breakdown["portfolio"] = c9
        total += c9["earned"]

        # ── Criterion 10: Screening Q&A ────────────────────────────────────
        c10 = _score_screening(app, job, weights["screening"])
        breakdown["screening"] = c10
        total += c10["earned"]

        total = round(min(100.0, max(0.0, total)), 2)

        # Step 5 — Auto-reject if below threshold ───────────────────────────
        auto_reject = flt(job.get("ec_auto_reject_below", 0))
        if auto_reject > 0 and total < auto_reject:
            frappe.db.set_value("Job Applicant", job_applicant, "status", "Rejected")

        # Save ──────────────────────────────────────────────────────────────
        frappe.db.set_value("Job Applicant", job_applicant, {
            "ec_total_score":    total,
            "ec_score_breakdown":json.dumps(breakdown),
            "ec_scoring_status": "Scored",
        })
        frappe.db.commit()

    except Exception as e:
        frappe.db.set_value("Job Applicant", job_applicant, "ec_scoring_status", "Error")
        frappe.db.commit()
        frappe.log_error(f"score_applicant({job_applicant}): {e}", "Recruitment Scoring")


@frappe.whitelist()
def rescore_applicant(job_applicant: str):
    app_doc = frappe.get_doc("Job Applicant", job_applicant)
    frappe.db.set_value("Job Applicant", job_applicant, {
        "ec_scoring_status": "Pending",
        "ec_is_duplicate":   0,
        "ec_knockout_passed":1,
        "ec_knockout_failed_reason": "",
    })
    score_applicant(job_applicant, app_doc.job_title)
    return {"status": "rescored",
            "new_score": frappe.db.get_value("Job Applicant", job_applicant, "ec_total_score")}


@frappe.whitelist()
def get_score_detail(job_applicant: str):
    vals = frappe.db.get_value(
        "Job Applicant", job_applicant,
        ["ec_total_score", "ec_score_breakdown", "ec_scoring_status",
         "ec_knockout_passed", "ec_knockout_failed_reason",
         "ec_is_duplicate", "ec_duplicate_of"],
        as_dict=True,
    )
    if not vals:
        frappe.throw("Applicant not found")
    try:
        breakdown = json.loads(vals.ec_score_breakdown or "{}")
    except Exception:
        breakdown = {}
    return {
        "total":                   flt(vals.ec_total_score),
        "breakdown":               breakdown,
        "status":                  vals.ec_scoring_status,
        "knockout_passed":         bool(vals.ec_knockout_passed),
        "knockout_failed_reason":  vals.ec_knockout_failed_reason or "",
        "is_duplicate":            bool(vals.ec_is_duplicate),
        "duplicate_of":            vals.ec_duplicate_of or "",
    }


# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _get_job(job_opening: str) -> dict:
    return frappe.db.get_value(
        "Job Opening", job_opening,
        ["name", "ec_scoring_enabled",
         "ec_education_level", "ec_field_of_study",
         "ec_experience_years_min", "ec_experience_years_max",
         "ec_skills_required", "ec_nice_to_have_skills",
         "ec_required_certifications", "ec_preferred_certifications",
         "ec_required_industry", "ec_related_industries",
         "ec_required_location_city", "ec_required_location_country",
         "ec_location_mode",
         "ec_required_languages",
         "ec_min_stability_years",
         "ec_portfolio_required",
         "ec_screening_questions",
         "ec_weight_education", "ec_weight_experience", "ec_weight_skills",
         "ec_weight_certifications", "ec_weight_industry", "ec_weight_location",
         "ec_weight_languages", "ec_weight_stability", "ec_weight_portfolio",
         "ec_weight_screening",
         "ec_pass_score", "ec_auto_reject_below"],
        as_dict=True,
    )


def _normalize_weights(job: dict) -> dict:
    """
    Read the 10 weight fields and normalise so their sum equals 100.
    Returns a dict keyed by criterion name.
    """
    raw = {
        "education":      flt(job.get("ec_weight_education")     or 15),
        "experience":     flt(job.get("ec_weight_experience")    or 25),
        "skills":         flt(job.get("ec_weight_skills")        or 30),
        "certifications": flt(job.get("ec_weight_certifications")or 10),
        "industry":       flt(job.get("ec_weight_industry")      or 10),
        "location":       flt(job.get("ec_weight_location")      or  5),
        "languages":      flt(job.get("ec_weight_languages")     or  5),
        "stability":      flt(job.get("ec_weight_stability")     or  5),
        "portfolio":      flt(job.get("ec_weight_portfolio")     or  5),
        "screening":      flt(job.get("ec_weight_screening")     or 10),
    }
    total = sum(raw.values()) or 100
    # Normalise so total == 100
    return {k: (v / total) * 100 for k, v in raw.items()}


def _candidate_text(app) -> str:
    """Build a searchable corpus from all free-text applicant fields."""
    parts = [
        app.ec_skills or "",
        app.ec_cover_letter or "",
        app.ec_certifications or "",
        app.ec_industry_experience or "",
        app.ec_languages or "",
        app.ec_screening_answers or "",
        app.ec_field_of_study or "",
        app.ec_employment_history or "",
    ]
    return " ".join(parts).lower()


def _csv_list(val: str) -> list[str]:
    """Split a comma-separated value string into a clean lowercase list."""
    return [s.strip().lower() for s in (val or "").split(",") if s.strip()]


# ── Criterion 1: Education ────────────────────────────────────────────────────

def _score_education(app, job, weight: float) -> dict:
    app_rank = EDUCATION_RANK.get(app.ec_education_level or "", 0)
    req_rank = EDUCATION_RANK.get(job.get("ec_education_level") or "", 0)

    # Level score (0–100)
    if req_rank == 0:
        level_raw = 100  # No requirement → full score
    elif app_rank >= req_rank:
        # Exceeds by one → +5, by two → +10 (cap 100)
        level_raw = min(100, 80 + (app_rank - req_rank) * 10)
    else:
        gap = req_rank - app_rank
        level_raw = max(0, 60 - gap * 20)

    # Field of study bonus (up to +20 on top of level)
    field_bonus = 0
    required_fields = _csv_list(job.get("ec_field_of_study") or "")
    if required_fields and app.ec_field_of_study:
        app_field = (app.ec_field_of_study or "").lower()
        for f in required_fields:
            if f in app_field or app_field in f:
                field_bonus = 20
                break
            # Partial match
            if any(word in app_field for word in f.split()):
                field_bonus = 10

    raw = min(100, level_raw + field_bonus)
    earned = (raw / 100) * weight

    return {
        "label":         "Education",
        "icon":          "🎓",
        "raw":           round(raw, 1),
        "weight":        round(weight, 1),
        "earned":        round(earned, 2),
        "applicant_edu": app.ec_education_level or "Not stated",
        "required_edu":  job.get("ec_education_level") or "Any",
        "field_of_study":app.ec_field_of_study or "—",
        "field_bonus":   field_bonus,
    }


# ── Criterion 2: Experience ───────────────────────────────────────────────────

def _score_experience(app, job, weight: float) -> dict:
    app_exp = flt(app.ec_experience_years or 0)
    req_min = flt(job.get("ec_experience_years_min") or 0)
    req_max = flt(job.get("ec_experience_years_max") or 0)  # 0 = no limit

    if req_min == 0:
        raw = 100
    elif app_exp >= req_min:
        # Bonus for exceeding (up to +20), penalise over-qualification
        excess = app_exp - req_min
        raw = min(100, 80 + excess * 4)
        if req_max > 0 and app_exp > req_max:
            raw = max(50, raw - (app_exp - req_max) * 10)
    else:
        ratio = app_exp / req_min
        raw = max(0, ratio * 75)

    earned = (raw / 100) * weight
    return {
        "label":        "Experience",
        "icon":         "💼",
        "raw":          round(raw, 1),
        "weight":       round(weight, 1),
        "earned":       round(earned, 2),
        "applicant_exp":f"{app_exp} years",
        "required_exp": f"{req_min}+ years" + (f" (max {req_max})" if req_max else ""),
    }


# ── Criterion 3: Skills ───────────────────────────────────────────────────────

def _score_skills(app, job, weight: float) -> dict:
    required    = _csv_list(job.get("ec_skills_required") or "")
    nice_to_have= _csv_list(job.get("ec_nice_to_have_skills") or "")
    corpus      = _candidate_text(app)

    req_matched   = [s for s in required    if s in corpus]
    req_missing   = [s for s in required    if s not in corpus]
    nth_matched   = [s for s in nice_to_have if s in corpus]
    nth_missing   = [s for s in nice_to_have if s not in corpus]

    # Required skills: 0–70 points of this criterion
    # Nice-to-have:    0–30 points
    if required:
        req_score = (len(req_matched) / len(required)) * 70
    else:
        req_score = 70  # No required skills → full required portion

    if nice_to_have:
        nth_score = (len(nth_matched) / len(nice_to_have)) * 30
    else:
        nth_score = 30  # No NTH skills → full NTH portion

    raw    = min(100, req_score + nth_score)
    earned = (raw / 100) * weight

    return {
        "label":            "Skills",
        "icon":             "🧠",
        "raw":              round(raw, 1),
        "weight":           round(weight, 1),
        "earned":           round(earned, 2),
        "required_matched": req_matched[:15],
        "required_missing": req_missing[:15],
        "nth_matched":      nth_matched[:10],
        "nth_missing":      nth_missing[:10],
        "req_count":        len(required),
        "nth_count":        len(nice_to_have),
    }


# ── Criterion 4: Certifications ───────────────────────────────────────────────

def _score_certifications(app, job, weight: float) -> dict:
    required  = _csv_list(job.get("ec_required_certifications") or "")
    preferred = _csv_list(job.get("ec_preferred_certifications") or "")
    corpus    = _candidate_text(app)

    req_match  = [c for c in required  if c in corpus]
    req_miss   = [c for c in required  if c not in corpus]
    pref_match = [c for c in preferred if c in corpus]

    if not required and not preferred:
        raw = 100
    else:
        # Required certs: 0–70, preferred: 0–30
        req_raw  = (len(req_match)  / len(required) * 70)  if required  else 70
        pref_raw = (len(pref_match) / len(preferred) * 30) if preferred else 30
        raw = min(100, req_raw + pref_raw)

    earned = (raw / 100) * weight
    return {
        "label":              "Certifications",
        "icon":               "📜",
        "raw":                round(raw, 1),
        "weight":             round(weight, 1),
        "earned":             round(earned, 2),
        "required_matched":   req_match,
        "required_missing":   req_miss,
        "preferred_matched":  pref_match,
    }


# ── Criterion 5: Industry Experience ─────────────────────────────────────────

def _score_industry(app, job, weight: float) -> dict:
    target  = (job.get("ec_required_industry") or "").lower().strip()
    related = _csv_list(job.get("ec_related_industries") or "")
    corpus  = _candidate_text(app)

    if not target and not related:
        raw = 100
        match_type = "not_required"
    elif target and target in corpus:
        raw = 100
        match_type = "exact"
    else:
        partial = any(r in corpus for r in related)
        if partial:
            raw = 60
            match_type = "related"
        else:
            raw = 0
            match_type = "none"

    earned = (raw / 100) * weight
    return {
        "label":      "Industry Experience",
        "icon":       "🏭",
        "raw":        round(raw, 1),
        "weight":     round(weight, 1),
        "earned":     round(earned, 2),
        "match_type": match_type,
        "target":     target or "Any",
        "related":    related,
    }


# ── Criterion 6: Location ─────────────────────────────────────────────────────

def _score_location(app, job, weight: float) -> dict:
    req_city    = (job.get("ec_required_location_city")    or "").lower().strip()
    req_country = (job.get("ec_required_location_country") or "").lower().strip()
    mode        = (job.get("ec_location_mode") or "").lower()
    app_city    = (app.ec_current_city    or "").lower().strip()
    app_country = (app.ec_current_country or "").lower().strip()
    willing     = bool(app.ec_willing_to_relocate)

    # Remote positions: full score for everyone
    if mode == "remote":
        raw = 100
        reason = "Remote position — location not required"
    elif not req_city and not req_country:
        raw = 100
        reason = "No location requirement"
    elif req_city and app_city and req_city in app_city:
        raw = 100
        reason = "Same city"
    elif req_country and app_country and req_country in app_country:
        raw = 70 if req_city else 100
        reason = "Same country"
    elif willing:
        raw = 60
        reason = "Willing to relocate"
    else:
        raw = 0
        reason = "Location mismatch"

    earned = (raw / 100) * weight
    return {
        "label":    "Location",
        "icon":     "🌍",
        "raw":      round(raw, 1),
        "weight":   round(weight, 1),
        "earned":   round(earned, 2),
        "reason":   reason,
        "applicant":f"{app_city}, {app_country}".strip(", ") or "Not stated",
        "required": f"{req_city}, {req_country}".strip(", ") or "Any",
        "mode":     mode or "on-site",
    }


# ── Criterion 7: Language Skills ──────────────────────────────────────────────

def _score_languages(app, job, weight: float) -> dict:
    corpus = _candidate_text(app)
    required_json = job.get("ec_required_languages") or "[]"

    try:
        requirements = json.loads(required_json) if isinstance(required_json, str) else required_json
    except Exception:
        requirements = []

    if not requirements:
        return {"label":"Languages","icon":"🗣️","raw":100,"weight":round(weight,1),"earned":round(weight,2),"detail":[]}

    required_langs   = [r for r in requirements if r.get("level") == "required"]
    preferred_langs  = [r for r in requirements if r.get("level") == "preferred"]
    bonus_langs      = [r for r in requirements if r.get("level") == "bonus"]

    req_matched   = [l for l in required_langs  if l["lang"].lower() in corpus]
    pref_matched  = [l for l in preferred_langs if l["lang"].lower() in corpus]
    bonus_matched = [l for l in bonus_langs     if l["lang"].lower() in corpus]

    if required_langs:
        req_raw = (len(req_matched) / len(required_langs)) * 70
    else:
        req_raw = 70
    if preferred_langs:
        pref_raw = (len(pref_matched) / len(preferred_langs)) * 20
    else:
        pref_raw = 20
    if bonus_langs:
        bonus_raw = (len(bonus_matched) / len(bonus_langs)) * 10
    else:
        bonus_raw = 10

    raw = min(100, req_raw + pref_raw + bonus_raw)
    earned = (raw / 100) * weight

    return {
        "label":    "Languages",
        "icon":     "🗣️",
        "raw":      round(raw, 1),
        "weight":   round(weight, 1),
        "earned":   round(earned, 2),
        "required_matched":  [l["lang"] for l in req_matched],
        "required_missing":  [l["lang"] for l in required_langs if l not in req_matched],
        "preferred_matched": [l["lang"] for l in pref_matched],
        "bonus_matched":     [l["lang"] for l in bonus_matched],
    }


# ── Criterion 8: Employment Stability ────────────────────────────────────────

def _score_stability(app, job, weight: float, avg_duration: float) -> dict:
    threshold = flt(job.get("ec_min_stability_years") or 0)

    if threshold == 0:
        raw = 100
        reason = "Stability not required"
    elif avg_duration <= 0:
        raw = 70  # Unknown — neutral credit
        reason = "Employment history not provided"
    elif avg_duration >= threshold:
        bonus = min(20, (avg_duration - threshold) * 5)
        raw = min(100, 80 + bonus)
        reason = f"Avg {avg_duration:.1f} years/role (threshold {threshold})"
    else:
        ratio = avg_duration / threshold
        raw = max(0, ratio * 70)
        reason = f"Avg {avg_duration:.1f} years/role (below {threshold} threshold)"

    earned = (raw / 100) * weight
    return {
        "label":        "Employment Stability",
        "icon":         "📅",
        "raw":          round(raw, 1),
        "weight":       round(weight, 1),
        "earned":       round(earned, 2),
        "avg_duration": round(avg_duration, 1),
        "threshold":    threshold,
        "reason":       reason,
    }


# ── Criterion 9: Portfolio ────────────────────────────────────────────────────

def _score_portfolio(app, job, weight: float) -> dict:
    required  = bool(cint(job.get("ec_portfolio_required") or 0))
    has_port  = bool(app.ec_portfolio_url and str(app.ec_portfolio_url).strip())
    has_github= bool(app.ec_github_url and str(app.ec_github_url).strip())

    if not required:
        # Bonus scoring: having portfolio even if not required
        if has_port and has_github:
            raw = 100
        elif has_port or has_github:
            raw = 80
        else:
            raw = 60  # Neutral — not penalised
    else:
        if has_port and has_github:
            raw = 100
        elif has_port or has_github:
            raw = 70
        else:
            raw = 0

    earned = (raw / 100) * weight
    return {
        "label":       "Portfolio / Projects",
        "icon":        "🧩",
        "raw":         round(raw, 1),
        "weight":      round(weight, 1),
        "earned":      round(earned, 2),
        "portfolio":   app.ec_portfolio_url or "",
        "github":      app.ec_github_url or "",
        "required":    required,
    }


# ── Criterion 10: Screening Q&A ───────────────────────────────────────────────

def _score_screening(app, job, weight: float) -> dict:
    questions_json = job.get("ec_screening_questions") or "[]"
    answers_raw    = app.ec_screening_answers or "[]"

    try:
        questions = json.loads(questions_json) if isinstance(questions_json, str) else questions_json
        answers   = json.loads(answers_raw)   if isinstance(answers_raw, str)    else answers_raw
        ans_map   = {str(a.get("id", a.get("question",""))): a.get("answer","")
                     for a in (answers if isinstance(answers, list) else [])}
    except Exception:
        questions, ans_map = [], {}

    if not questions:
        return {"label":"Screening Q&A","icon":"📝","raw":100,"weight":round(weight,1),"earned":round(weight,2),"detail":[]}

    q_total_w = sum(flt(q.get("weight", 1)) for q in questions) or 1
    q_earned  = 0.0
    detail    = []

    for q in questions:
        qid     = str(q.get("id", q.get("question", "")))
        qtype   = q.get("type", "text")
        qweight = flt(q.get("weight", 1))
        correct = q.get("correct_answer", "")
        answer  = ans_map.get(qid, "")
        q_score = 0.0

        if qtype in ("yesno", "mcq") and correct:
            q_score = 100.0 if str(answer).strip().lower() == str(correct).strip().lower() else 0.0
        elif qtype == "rating":
            try:
                val        = float(answer or 0)
                max_rating = float(q.get("max_rating", 5))
                q_score    = (val / max_rating) * 100
            except Exception:
                q_score = 0.0
        else:
            text = str(answer).strip()
            if len(text) > 100:
                q_score = 90.0
            elif len(text) > 30:
                q_score = 70.0
            elif len(text) > 5:
                q_score = 40.0
            else:
                q_score = 0.0

        q_earned += (q_score / 100) * qweight
        detail.append({
            "question": q.get("question", qid),
            "type":     qtype,
            "answer":   str(answer)[:300],
            "score":    round(q_score, 1),
            "weight":   qweight,
        })

    raw    = (q_earned / q_total_w) * 100
    earned = (raw / 100) * weight
    return {
        "label":  "Screening Q&A",
        "icon":   "📝",
        "raw":    round(raw, 1),
        "weight": round(weight, 1),
        "earned": round(earned, 2),
        "detail": detail,
    }


# ── Knock-out logic ───────────────────────────────────────────────────────────

def _check_knockout(app, job: dict) -> dict:
    """
    Evaluate knock-out questions.
    A question marked knockout:true with a required knockout_answer auto-rejects
    the applicant if they give the wrong answer.
    Returns {"passed": bool, "reason": str}
    """
    questions_json = job.get("ec_screening_questions") or "[]"
    answers_raw    = app.ec_screening_answers or "[]"

    try:
        questions = json.loads(questions_json) if isinstance(questions_json, str) else questions_json
        answers   = json.loads(answers_raw)    if isinstance(answers_raw, str)    else answers_raw
        ans_map   = {str(a.get("id", a.get("question",""))): a.get("answer","")
                     for a in (answers if isinstance(answers, list) else [])}
    except Exception:
        return {"passed": True, "reason": ""}

    ko_questions = [q for q in questions if q.get("knockout")]
    for q in ko_questions:
        qid     = str(q.get("id", q.get("question", "")))
        correct = str(q.get("knockout_answer", q.get("correct_answer", ""))).strip().lower()
        given   = str(ans_map.get(qid, "")).strip().lower()
        if correct and given != correct:
            return {
                "passed": False,
                "reason": f"Knock-out question failed: \"{q.get('question', qid)}\" — required: {correct}, given: {given}"
            }

    return {"passed": True, "reason": ""}


# ── Duplicate detection ───────────────────────────────────────────────────────

def _check_duplicate(app, job_opening: str) -> str | None:
    """
    Return the name of an earlier application for the same email + job,
    or None if no duplicate found.
    """
    existing = frappe.db.sql("""
        SELECT name FROM `tabJob Applicant`
        WHERE job_title = %s
          AND email_id  = %s
          AND name      != %s
          AND docstatus != 2
        ORDER BY creation ASC LIMIT 1
    """, (job_opening, (app.email_id or "").lower().strip(), app.name), as_dict=True)
    return existing[0].name if existing else None


# ── Employment stability helper ───────────────────────────────────────────────

def _compute_avg_duration(app) -> float:
    """
    Parse ec_employment_history JSON and compute average job duration in years.
    Format: [{"from":"2020-01","to":"2023-06"}, ...]
    """
    try:
        history = json.loads(app.ec_employment_history or "[]")
        if not history:
            return 0.0
        durations = []
        for job in history:
            from_str = job.get("from", "")
            to_str   = job.get("to", "") or datetime.now().strftime("%Y-%m")
            if not from_str:
                continue
            try:
                fmt = "%Y-%m"
                d_from = datetime.strptime(from_str[:7], fmt)
                d_to   = datetime.strptime(to_str[:7],   fmt)
                months = max(0, (d_to.year - d_from.year) * 12 + (d_to.month - d_from.month))
                durations.append(months / 12)
            except Exception:
                pass
        return round(sum(durations) / len(durations), 2) if durations else 0.0
    except Exception:
        return 0.0


# ── Notify knock-out ──────────────────────────────────────────────────────────

def _notify_knockout(app_doc, reason: str):
    if not app_doc.email_id:
        return
    token = app_doc.ec_portal_token or ""
    frappe.sendmail(
        recipients=[app_doc.email_id],
        subject=f"Application Update — {app_doc.job_title}",
        message=f"""
<p>Dear {app_doc.applicant_name},</p>
<p>Thank you for your interest in the <strong>{app_doc.job_title}</strong> position.</p>
<p>After reviewing your responses to our screening questions, we regret to inform you that we are unable to proceed with your application at this time.</p>
<p style="color:#64748b;font-size:12px;margin-top:16px">We appreciate you taking the time to apply and encourage you to apply for future roles that match your profile.</p>
        """,
        now=True,
    )