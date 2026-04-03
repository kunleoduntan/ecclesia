# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/api/recruitment_portal_custom_fields.py
# Full 10-criteria scoring system — all custom fields

import frappe

# ── Job Opening fields ────────────────────────────────────────────────────────
JOB_OPENING_FIELDS = [
    # ── Section: Portal ──────────────────────────────────────────────────────
    {"fieldname": "ec_portal_section",        "fieldtype": "Section Break",  "label": "Ecclesia Portal",                     "insert_after": "description"},
    {"fieldname": "ec_portal_published",      "fieldtype": "Check",          "label": "Published on Careers Portal",         "default": "1",  "insert_after": "ec_portal_section"},
    {"fieldname": "ec_application_deadline",  "fieldtype": "Date",           "label": "Application Deadline",               "insert_after": "ec_portal_published"},
    {"fieldname": "ec_location_mode",         "fieldtype": "Select",         "label": "Work Mode",
     "options": "\nOn-site\nRemote\nHybrid",                                                                                  "insert_after": "ec_application_deadline"},
    {"fieldname": "ec_portal_col",            "fieldtype": "Column Break",                                                   "insert_after": "ec_location_mode"},
    {"fieldname": "ec_salary_min",            "fieldtype": "Currency",       "label": "Salary Min",                         "insert_after": "ec_portal_col"},
    {"fieldname": "ec_salary_max",            "fieldtype": "Currency",       "label": "Salary Max",                         "insert_after": "ec_salary_min"},

    # ── Section: Criteria 1 — Education ──────────────────────────────────────
    {"fieldname": "ec_edu_section",           "fieldtype": "Section Break",  "label": "Criteria 1 — Education",             "insert_after": "ec_salary_max"},
    {"fieldname": "ec_education_level",       "fieldtype": "Select",         "label": "Minimum Education Level",
     "options": "\nHigh School\nOND / NCE\nHND\nBachelor's Degree\nPostgraduate Diploma\nMaster's Degree\nDoctorate / PhD",  "insert_after": "ec_edu_section"},
    {"fieldname": "ec_field_of_study",        "fieldtype": "Text",           "label": "Relevant Fields of Study (comma-sep)","insert_after": "ec_education_level"},
    {"fieldname": "ec_edu_col",               "fieldtype": "Column Break",                                                   "insert_after": "ec_field_of_study"},
    {"fieldname": "ec_weight_education",      "fieldtype": "Float",          "label": "Weight: Education (%)",              "default": "15", "insert_after": "ec_edu_col"},

    # ── Section: Criteria 2 — Experience ─────────────────────────────────────
    {"fieldname": "ec_exp_section",           "fieldtype": "Section Break",  "label": "Criteria 2 — Experience",            "insert_after": "ec_weight_education"},
    {"fieldname": "ec_experience_years_min",  "fieldtype": "Float",          "label": "Min Experience (Years)",             "insert_after": "ec_exp_section"},
    {"fieldname": "ec_experience_years_max",  "fieldtype": "Float",          "label": "Max Experience (Years, 0=no limit)",  "default": "0",  "insert_after": "ec_experience_years_min"},
    {"fieldname": "ec_exp_col",               "fieldtype": "Column Break",                                                   "insert_after": "ec_experience_years_max"},
    {"fieldname": "ec_weight_experience",     "fieldtype": "Float",          "label": "Weight: Experience (%)",             "default": "25", "insert_after": "ec_exp_col"},

    # ── Section: Criteria 3 — Skills ─────────────────────────────────────────
    {"fieldname": "ec_skills_section",        "fieldtype": "Section Break",  "label": "Criteria 3 — Skills",                "insert_after": "ec_weight_experience"},
    {"fieldname": "ec_skills_required",       "fieldtype": "Text",           "label": "Required Skills (comma-sep, +10 each)","insert_after": "ec_skills_section"},
    {"fieldname": "ec_nice_to_have_skills",   "fieldtype": "Text",           "label": "Nice-to-Have Skills (comma-sep, +5 each)","insert_after": "ec_skills_required"},
    {"fieldname": "ec_skills_col",            "fieldtype": "Column Break",                                                   "insert_after": "ec_nice_to_have_skills"},
    {"fieldname": "ec_weight_skills",         "fieldtype": "Float",          "label": "Weight: Skills (%)",                 "default": "30", "insert_after": "ec_skills_col"},

    # ── Section: Criteria 4 — Certifications ─────────────────────────────────
    {"fieldname": "ec_cert_section",          "fieldtype": "Section Break",  "label": "Criteria 4 — Certifications",        "insert_after": "ec_weight_skills"},
    {"fieldname": "ec_required_certifications","fieldtype":"Text",           "label": "Required Certifications (comma-sep)", "insert_after": "ec_cert_section"},
    {"fieldname": "ec_preferred_certifications","fieldtype":"Text",          "label": "Preferred Certifications (comma-sep)","insert_after": "ec_required_certifications"},
    {"fieldname": "ec_cert_col",              "fieldtype": "Column Break",                                                   "insert_after": "ec_preferred_certifications"},
    {"fieldname": "ec_weight_certifications", "fieldtype": "Float",          "label": "Weight: Certifications (%)",         "default": "10", "insert_after": "ec_cert_col"},

    # ── Section: Criteria 5 — Industry ───────────────────────────────────────
    {"fieldname": "ec_industry_section",      "fieldtype": "Section Break",  "label": "Criteria 5 — Industry Experience",   "insert_after": "ec_weight_certifications"},
    {"fieldname": "ec_required_industry",     "fieldtype": "Data",           "label": "Target Industry (e.g. Finance)",     "insert_after": "ec_industry_section"},
    {"fieldname": "ec_related_industries",    "fieldtype": "Text",           "label": "Related Industries (comma-sep)",      "insert_after": "ec_required_industry"},
    {"fieldname": "ec_industry_col",          "fieldtype": "Column Break",                                                   "insert_after": "ec_related_industries"},
    {"fieldname": "ec_weight_industry",       "fieldtype": "Float",          "label": "Weight: Industry (%)",               "default": "10", "insert_after": "ec_industry_col"},

    # ── Section: Criteria 6 — Location ───────────────────────────────────────
    {"fieldname": "ec_loc_section",           "fieldtype": "Section Break",  "label": "Criteria 6 — Location",              "insert_after": "ec_weight_industry"},
    {"fieldname": "ec_required_location_city","fieldtype": "Data",           "label": "Preferred City",                     "insert_after": "ec_loc_section"},
    {"fieldname": "ec_required_location_country","fieldtype":"Data",         "label": "Required Country",                   "insert_after": "ec_required_location_city"},
    {"fieldname": "ec_loc_col",               "fieldtype": "Column Break",                                                   "insert_after": "ec_required_location_country"},
    {"fieldname": "ec_weight_location",       "fieldtype": "Float",          "label": "Weight: Location (%)",               "default": "5",  "insert_after": "ec_loc_col"},

    # ── Section: Criteria 7 — Languages ──────────────────────────────────────
    {"fieldname": "ec_lang_section",          "fieldtype": "Section Break",  "label": "Criteria 7 — Language Skills",       "insert_after": "ec_weight_location"},
    {"fieldname": "ec_required_languages",    "fieldtype": "Long Text",      "label": "Language Requirements (JSON)",
     "description": '[{"lang":"English","level":"required"},{"lang":"French","level":"preferred"}]',                         "insert_after": "ec_lang_section"},
    {"fieldname": "ec_lang_col",              "fieldtype": "Column Break",                                                   "insert_after": "ec_required_languages"},
    {"fieldname": "ec_weight_languages",      "fieldtype": "Float",          "label": "Weight: Languages (%)",              "default": "5",  "insert_after": "ec_lang_col"},

    # ── Section: Criteria 8 — Stability ──────────────────────────────────────
    {"fieldname": "ec_stability_section",     "fieldtype": "Section Break",  "label": "Criteria 8 — Employment Stability",  "insert_after": "ec_weight_languages"},
    {"fieldname": "ec_min_stability_years",   "fieldtype": "Float",          "label": "Min Avg Job Duration (Years, 0=off)", "default": "0",  "insert_after": "ec_stability_section"},
    {"fieldname": "ec_stability_col",         "fieldtype": "Column Break",                                                   "insert_after": "ec_min_stability_years"},
    {"fieldname": "ec_weight_stability",      "fieldtype": "Float",          "label": "Weight: Stability (%)",              "default": "5",  "insert_after": "ec_stability_col"},

    # ── Section: Criteria 9 — Portfolio ──────────────────────────────────────
    {"fieldname": "ec_portfolio_section",     "fieldtype": "Section Break",  "label": "Criteria 9 — Portfolio / Projects",  "insert_after": "ec_weight_stability"},
    {"fieldname": "ec_portfolio_required",    "fieldtype": "Check",          "label": "Portfolio / GitHub Required",        "default": "0",  "insert_after": "ec_portfolio_section"},
    {"fieldname": "ec_portfolio_col",         "fieldtype": "Column Break",                                                   "insert_after": "ec_portfolio_required"},
    {"fieldname": "ec_weight_portfolio",      "fieldtype": "Float",          "label": "Weight: Portfolio (%)",              "default": "5",  "insert_after": "ec_portfolio_col"},

    # ── Section: Criteria 10 — Screening / Cultural Fit ──────────────────────
    {"fieldname": "ec_screening_section",     "fieldtype": "Section Break",  "label": "Criteria 10 — Screening & Cultural Fit","insert_after": "ec_weight_portfolio"},
    {"fieldname": "ec_screening_questions",   "fieldtype": "Long Text",      "label": "Screening Questions (JSON)",
     "description": '[{"id":1,"question":"...","type":"yesno/mcq/text/rating","options":[],"required":true,"weight":1,"correct_answer":"","knockout":false,"knockout_answer":""}]',
                                                                                                                             "insert_after": "ec_screening_section"},
    {"fieldname": "ec_screening_col",         "fieldtype": "Column Break",                                                   "insert_after": "ec_screening_questions"},
    {"fieldname": "ec_weight_screening",      "fieldtype": "Float",          "label": "Weight: Screening Q&A (%)",          "default": "10", "insert_after": "ec_screening_col"},

    # ── Section: Auto-scoring settings ───────────────────────────────────────
    {"fieldname": "ec_scoring_section",       "fieldtype": "Section Break",  "label": "Auto-Scoring Settings",              "insert_after": "ec_weight_screening"},
    {"fieldname": "ec_scoring_enabled",       "fieldtype": "Check",          "label": "Enable Auto-Scoring",                "default": "1",  "insert_after": "ec_scoring_section"},
    {"fieldname": "ec_pass_score",            "fieldtype": "Float",          "label": "Pass Score Threshold (0–100)",        "default": "70", "insert_after": "ec_scoring_enabled"},
    {"fieldname": "ec_auto_reject_below",     "fieldtype": "Float",          "label": "Auto-Reject Score Below (0=off)",     "default": "0",  "insert_after": "ec_pass_score"},
]

# ── Job Applicant fields ───────────────────────────────────────────────────────
JOB_APPLICANT_FIELDS = [
    # ── Section: Portal metadata ──────────────────────────────────────────────
    {"fieldname": "ec_portal_section",        "fieldtype": "Section Break",  "label": "Ecclesia Portal Fields",              "insert_after": "resume_attachment"},
    {"fieldname": "ec_cv_file",               "fieldtype": "Attach",         "label": "CV / Resume File",                    "insert_after": "ec_portal_section"},
    {"fieldname": "ec_cover_letter",          "fieldtype": "Long Text",      "label": "Cover Letter",                        "insert_after": "ec_cv_file"},
    {"fieldname": "ec_applied_via_portal",    "fieldtype": "Check",          "label": "Applied via Portal",                  "default": "0",  "read_only": 1, "insert_after": "ec_cover_letter"},
    {"fieldname": "ec_portal_token",          "fieldtype": "Data",           "label": "Applicant Tracking Token",            "read_only": 1,  "insert_after": "ec_applied_via_portal"},

    # ── Criteria 1: Education ─────────────────────────────────────────────────
    {"fieldname": "ec_edu_section",           "fieldtype": "Section Break",  "label": "Education",                           "insert_after": "ec_portal_token"},
    {"fieldname": "ec_education_level",       "fieldtype": "Select",         "label": "Highest Education Level",
     "options": "\nHigh School\nOND / NCE\nHND\nBachelor's Degree\nPostgraduate Diploma\nMaster's Degree\nDoctorate / PhD",  "insert_after": "ec_edu_section"},
    {"fieldname": "ec_field_of_study",        "fieldtype": "Data",           "label": "Field of Study",                      "insert_after": "ec_education_level"},
    {"fieldname": "ec_university_name",       "fieldtype": "Data",           "label": "University / Institution",            "insert_after": "ec_field_of_study"},
    {"fieldname": "ec_graduation_year",       "fieldtype": "Int",            "label": "Graduation Year",                     "insert_after": "ec_university_name"},

    # ── Criteria 2: Experience ────────────────────────────────────────────────
    {"fieldname": "ec_exp_section",           "fieldtype": "Section Break",  "label": "Experience",                          "insert_after": "ec_graduation_year"},
    {"fieldname": "ec_experience_years",      "fieldtype": "Float",          "label": "Total Years of Experience",           "insert_after": "ec_exp_section"},
    {"fieldname": "ec_current_role",          "fieldtype": "Data",           "label": "Current / Last Role",                 "insert_after": "ec_experience_years"},
    {"fieldname": "ec_employment_history",    "fieldtype": "Long Text",      "label": "Employment History (JSON)",
     "description": '[{"company":"...","role":"...","from":"2020-01","to":"2023-06","industry":"..."}]',                       "insert_after": "ec_current_role"},
    {"fieldname": "ec_avg_job_duration",      "fieldtype": "Float",          "label": "Avg Job Duration (Years, auto-computed)", "read_only": 1, "insert_after": "ec_employment_history"},

    # ── Criteria 3: Skills ────────────────────────────────────────────────────
    {"fieldname": "ec_skills_section",        "fieldtype": "Section Break",  "label": "Skills",                              "insert_after": "ec_avg_job_duration"},
    {"fieldname": "ec_skills",                "fieldtype": "Text",           "label": "Skills (comma-sep)",                  "insert_after": "ec_skills_section"},

    # ── Criteria 4: Certifications ────────────────────────────────────────────
    {"fieldname": "ec_cert_section",          "fieldtype": "Section Break",  "label": "Certifications",                      "insert_after": "ec_skills"},
    {"fieldname": "ec_certifications",        "fieldtype": "Text",           "label": "Certifications (comma-sep)",          "insert_after": "ec_cert_section"},

    # ── Criteria 5: Industry ──────────────────────────────────────────────────
    {"fieldname": "ec_industry_section",      "fieldtype": "Section Break",  "label": "Industry",                            "insert_after": "ec_certifications"},
    {"fieldname": "ec_industry_experience",   "fieldtype": "Text",           "label": "Industries Worked In (comma-sep)",    "insert_after": "ec_industry_section"},

    # ── Criteria 6: Location ──────────────────────────────────────────────────
    {"fieldname": "ec_loc_section",           "fieldtype": "Section Break",  "label": "Location",                            "insert_after": "ec_industry_experience"},
    {"fieldname": "ec_current_city",          "fieldtype": "Data",           "label": "Current City",                        "insert_after": "ec_loc_section"},
    {"fieldname": "ec_current_country",       "fieldtype": "Data",           "label": "Current Country",                     "insert_after": "ec_current_city"},
    {"fieldname": "ec_willing_to_relocate",   "fieldtype": "Check",          "label": "Willing to Relocate",                 "default": "0", "insert_after": "ec_current_country"},
    {"fieldname": "ec_work_permit",           "fieldtype": "Data",           "label": "Work Permit / Eligibility",           "insert_after": "ec_willing_to_relocate"},

    # ── Criteria 7: Languages ─────────────────────────────────────────────────
    {"fieldname": "ec_lang_section",          "fieldtype": "Section Break",  "label": "Languages",                           "insert_after": "ec_work_permit"},
    {"fieldname": "ec_languages",             "fieldtype": "Text",           "label": "Languages (comma-sep, e.g. English, French)", "insert_after": "ec_lang_section"},

    # ── Criteria 8: Stability (computed) ─────────────────────────────────────
    # ec_avg_job_duration is already added above — computed from employment history

    # ── Criteria 9: Portfolio ─────────────────────────────────────────────────
    {"fieldname": "ec_portfolio_section",     "fieldtype": "Section Break",  "label": "Portfolio & Projects",                "insert_after": "ec_languages"},
    {"fieldname": "ec_portfolio_url",         "fieldtype": "Data",           "label": "Portfolio / Website URL",             "insert_after": "ec_portfolio_section"},
    {"fieldname": "ec_github_url",            "fieldtype": "Data",           "label": "GitHub / LinkedIn URL",               "insert_after": "ec_portfolio_url"},

    # ── Criteria 10: Screening answers ───────────────────────────────────────
    {"fieldname": "ec_screening_section",     "fieldtype": "Section Break",  "label": "Screening Answers",                   "insert_after": "ec_github_url"},
    {"fieldname": "ec_screening_answers",     "fieldtype": "Long Text",      "label": "Screening Answers (JSON)",            "insert_after": "ec_screening_section"},

    # ── Knock-out & Duplicate ─────────────────────────────────────────────────
    {"fieldname": "ec_ko_section",            "fieldtype": "Section Break",  "label": "Knock-out & Duplicate Detection",     "insert_after": "ec_screening_answers"},
    {"fieldname": "ec_knockout_passed",       "fieldtype": "Check",          "label": "Passed Knock-out Questions",          "default": "1", "read_only": 1, "insert_after": "ec_ko_section"},
    {"fieldname": "ec_knockout_failed_reason","fieldtype": "Small Text",     "label": "Knock-out Fail Reason",               "read_only": 1, "insert_after": "ec_knockout_passed"},
    {"fieldname": "ec_is_duplicate",          "fieldtype": "Check",          "label": "Duplicate Application",               "default": "0", "read_only": 1, "insert_after": "ec_knockout_failed_reason"},
    {"fieldname": "ec_duplicate_of",          "fieldtype": "Link",           "label": "Duplicate of",                        "options": "Job Applicant", "read_only": 1, "insert_after": "ec_is_duplicate"},

    # ── Scoring outputs ───────────────────────────────────────────────────────
    {"fieldname": "ec_scoring_section",       "fieldtype": "Section Break",  "label": "Scoring Results",                     "insert_after": "ec_duplicate_of"},
    {"fieldname": "ec_total_score",           "fieldtype": "Float",          "label": "Total Score (0–100)",                 "read_only": 1, "insert_after": "ec_scoring_section"},
    {"fieldname": "ec_score_breakdown",       "fieldtype": "Long Text",      "label": "Score Breakdown (JSON)",              "read_only": 1, "insert_after": "ec_total_score"},
    {"fieldname": "ec_scoring_status",        "fieldtype": "Select",         "label": "Scoring Status",
     "options": "Pending\nScored\nError\nKnocked Out\nDuplicate",                                                             "default": "Pending", "read_only": 1, "insert_after": "ec_score_breakdown"},

    # ── CV Parse data ─────────────────────────────────────────────────────────
    {"fieldname": "ec_cv_section",            "fieldtype": "Section Break",  "label": "CV Parse Data",                       "insert_after": "ec_scoring_status"},
    {"fieldname": "ec_cv_parsed",             "fieldtype": "Check",          "label": "CV Parsed",                           "default": "0", "read_only": 1, "insert_after": "ec_cv_section"},
    {"fieldname": "ec_cv_parse_data",         "fieldtype": "Long Text",      "label": "Parsed CV Data (JSON)",               "read_only": 1, "insert_after": "ec_cv_parsed"},
]

CUSTOM_FIELDS = {
    "Job Opening":   JOB_OPENING_FIELDS,
    "Job Applicant": JOB_APPLICANT_FIELDS,
    "Interview": [
        {"fieldname": "ec_interview_section",  "fieldtype": "Section Break",  "label": "Ecclesia Fields",          "insert_after": "end_time"},
        {"fieldname": "ec_meeting_link",       "fieldtype": "Data",           "label": "Meeting Link",             "insert_after": "ec_interview_section"},
        {"fieldname": "ec_candidate_notified", "fieldtype": "Check",          "label": "Candidate Notified",       "read_only": 1, "insert_after": "ec_meeting_link"},
        {"fieldname": "ec_interview_notes",    "fieldtype": "Long Text",      "label": "Interview Notes",          "insert_after": "ec_candidate_notified"},
    ],
}


def after_migrate():
    install_custom_fields()


@frappe.whitelist()
def install_custom_fields():
    installed = 0
    skipped   = 0
    errors    = []

    for doctype, fields in CUSTOM_FIELDS.items():
        for f in fields:
            # ✅ Frappe names Custom Fields as "{DocType}-{fieldname}"
            key = f"{doctype}-{f['fieldname']}"

            if frappe.db.exists("Custom Field", key):
                skipped += 1
                continue

            try:
                cf = frappe.get_doc({
                    "doctype":      "Custom Field",
                    "dt":           doctype,
                    "module":       "Ecclesia",
                    "fieldname":    f["fieldname"],
                    "fieldtype":    f["fieldtype"],
                    "label":        f.get("label", ""),
                    "options":      f.get("options", ""),
                    "default":      f.get("default", ""),
                    "description":  f.get("description", ""),
                    "insert_after": f.get("insert_after", ""),
                    "read_only":    f.get("read_only", 0),
                })
                cf.insert(ignore_permissions=True)
                installed += 1

            except Exception as e:
                errors.append(f"{doctype}.{f['fieldname']}: {e}")
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Recruitment CF Failed: {doctype}.{f['fieldname']}"
                )

    frappe.db.commit()

    return {
        "status":    "ok",
        "installed": installed,
        "skipped":   skipped,
        "errors":    errors,
    }