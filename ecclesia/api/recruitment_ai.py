"""
ecclesia/api/recruitment_ai.py
================================
Whitelisted API functions for AI-powered recruitment features.
Separated from the DocType controller so they can be called
via frappe.call() from the desk or frappe.enqueue() from background jobs.

Place at: ecclesia/ecclesia/api/recruitment_ai.py
"""
import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def generate_candidate_comparison(matrix_name):
    """
    Generate an AI narrative comparing all candidates in a
    Candidate Comparison Matrix document.

    Called from:
      - CandidateComparisonMatrix.on_submit  via frappe.enqueue
      - candidate_comparison_matrix.js       via frappe.call (Generate AI Comparison button)
    """
    try:
        import requests

        doc = frappe.get_doc("Candidate Comparison Matrix", matrix_name)

        if not doc.candidates:
            return {"error": "No candidates in matrix"}

        # Build one descriptive line per candidate.
        # Using a list + sep.join() avoids the backslash-in-expression
        # SyntaxError that occurs in Python 3.12+ when \n appears
        # inside an f-string expression.
        sep = "\n"
        lines = []
        for r in sorted(doc.candidates, key=lambda x: flt(x.total_score), reverse=True):
            lines.append(
                "- {name}: Score {score}%, AI verdict: {verdict}, Rank #{rank}".format(
                    name=r.candidate_name,
                    score=r.total_score,
                    verdict=r.ai_recommendation or "Not assessed",
                    rank=r.hr_rank,
                )
            )
        candidates_text = sep.join(lines)

        prompt = (
            "You are an HR consultant. Compare these candidates for the position: {opening}.\n\n"
            "Candidates:\n{candidates}\n\n"
            "In 3-4 sentences, explain who the top candidates are and why, "
            "and any considerations HR should weigh. Be specific and professional. "
            "Do not use markdown formatting."
        ).format(opening=doc.job_opening, candidates=candidates_text)

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 350,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=25
        )

        if resp.ok:
            text = resp.json().get("content", [{}])[0].get("text", "")
            if text:
                frappe.db.set_value(
                    "Candidate Comparison Matrix",
                    matrix_name,
                    "ai_comparison",
                    text
                )
                frappe.db.commit()
                return {"success": True, "narrative": text}

        return {"error": "AI API returned non-200 status"}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Candidate Comparison AI Error")
        return {"error": "AI generation failed. Check error log."}


@frappe.whitelist()
def get_ai_candidate_brief(resume_name):
    """
    Generate a one-paragraph executive brief for a single candidate.
    Called from the Resume Screening Result form's quick-action button.
    """
    try:
        import requests

        resume = frappe.get_doc("Resume", resume_name)

        result = frappe.db.get_value(
            "Resume Screening Result",
            {"resume": resume_name},
            ["total_score", "auto_decision", "matched_skills",
             "missing_mandatory_skills", "ai_narrative"],
            as_dict=True
        ) or {}

        prompt = (
            "Write a two-sentence executive brief for a recruiter about this candidate. "
            "Be factual, specific, and professional.\n\n"
            "Candidate: {name}\n"
            "Education: {edu} ({cls})\n"
            "Experience: {exp} years\n"
            "Skills: {skills}\n"
            "Certifications: {certs}\n"
            "Screening Score: {score}%\n"
            "Decision: {decision}\n"
            "Matched Skills: {matched}\n"
        ).format(
            name=resume.candidate_name,
            edu=resume.parsed_education or "Not stated",
            cls=frappe.db.get_value("Job Applicant", resume.job_applicant,
                                    "custom_degree_class") or "Not stated",
            exp=resume.parsed_years_experience or 0,
            skills=resume.parsed_skills or "Not stated",
            certs=resume.parsed_certifications or "None",
            score=result.get("total_score", 0),
            decision=result.get("auto_decision", "Pending"),
            matched=result.get("matched_skills", "None"),
        )

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )
        if resp.ok:
            text = resp.json().get("content", [{}])[0].get("text", "")
            return {"brief": text.strip()}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Candidate Brief AI Error")

    return {"brief": "AI brief unavailable. Please check system logs."}