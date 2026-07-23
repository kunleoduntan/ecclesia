"""
ecclesia/api/recruitment_custom_fields.py  (v2 — updated)
==========================================================
Adds all custom fields to Job Applicant and Job Opening.
Now includes: degree class, location, salary expectation, gender.

Run after deployment:
  bench --site YOUR_SITE execute ecclesia.api.recruitment_custom_fields.create_all
  bench --site YOUR_SITE migrate
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {

    "Job Applicant": [

        # ── Personal & Contact ────────────────────────────────────────────
        {
            "fieldname":   "custom_section_personal",
            "fieldtype":   "Section Break",
            "label":       "Additional Personal Information",
            "insert_after":"phone_number",
        },
        {
            "fieldname":   "custom_gender",
            "fieldtype":   "Select",
            "label":       "Gender",
            "options":     "\nMale\nFemale\nNon-binary\nPrefer not to say",
            "insert_after":"custom_section_personal",
            "description": "Optional. Used only for anonymous diversity monitoring.",
        },
        {
            "fieldname":   "custom_date_of_birth",
            "fieldtype":   "Date",
            "label":       "Date of Birth",
            "insert_after":"custom_gender",
            "description": "Optional. Used to verify age eligibility where applicable.",
        },

        # ── Location ──────────────────────────────────────────────────────
        {
            "fieldname":   "custom_section_location",
            "fieldtype":   "Section Break",
            "label":       "Location",
            "insert_after":"custom_date_of_birth",
        },
        {
            "fieldname":   "custom_current_city",
            "fieldtype":   "Data",
            "label":       "Current City",
            "insert_after":"custom_section_location",
            "placeholder": "e.g. Lagos",
        },
        {
            "fieldname":   "custom_current_state",
            "fieldtype":   "Data",
            "label":       "Current State",
            "insert_after":"custom_current_city",
            "placeholder": "e.g. Lagos State",
        },
        {
            "fieldname":   "custom_col_location",
            "fieldtype":   "Column Break",
            "insert_after":"custom_current_state",
        },
        {
            "fieldname":   "custom_open_to_relocation",
            "fieldtype":   "Select",
            "label":       "Open to Relocation?",
            "options":     "\nYes\nNo\nDepends on role",
            "insert_after":"custom_col_location",
        },
        {
            "fieldname":   "custom_work_mode_preference",
            "fieldtype":   "Select",
            "label":       "Work Mode Preference",
            "options":     "\nOn-site\nHybrid\nFully Remote\nFlexible",
            "insert_after":"custom_open_to_relocation",
        },

        # ── Academic ──────────────────────────────────────────────────────
        {
            "fieldname":   "custom_section_academic",
            "fieldtype":   "Section Break",
            "label":       "Academic Qualifications",
            "insert_after":"custom_work_mode_preference",
        },
        {
            "fieldname":   "custom_highest_education",
            "fieldtype":   "Select",
            "label":       "Highest Education Level",
            "options":     "\nO-Level\nOND\nHND\nBSc / B.Eng\nMSc / MBA\nPhD",
            "insert_after":"custom_section_academic",
        },
        {
            "fieldname":   "custom_degree_class",
            "fieldtype":   "Select",
            "label":       "Class of Degree",
            "options":     "\nFirst Class\nSecond Class Upper\nSecond Class Lower\nThird Class\nPass\nNot Applicable",
            "insert_after":"custom_highest_education",
            "description": "For HND: Distinction / Upper Credit / Lower Credit. Select the closest equivalent.",
        },
        {
            "fieldname":   "custom_col_academic",
            "fieldtype":   "Column Break",
            "insert_after":"custom_degree_class",
        },
        {
            "fieldname":   "custom_institution",
            "fieldtype":   "Data",
            "label":       "Institution / University",
            "insert_after":"custom_col_academic",
            "placeholder": "e.g. University of Lagos",
        },
        {
            "fieldname":   "custom_course_studied",
            "fieldtype":   "Data",
            "label":       "Course / Field of Study",
            "insert_after":"custom_institution",
            "placeholder": "e.g. Accounting, Computer Science",
        },
        {
            "fieldname":   "custom_graduation_year",
            "fieldtype":   "Int",
            "label":       "Year of Graduation",
            "insert_after":"custom_course_studied",
        },

        # ── Experience & Skills ────────────────────────────────────────────
        {
            "fieldname":   "custom_section_experience",
            "fieldtype":   "Section Break",
            "label":       "Experience & Skills",
            "insert_after":"custom_graduation_year",
        },
        {
            "fieldname":   "custom_years_experience",
            "fieldtype":   "Float",
            "label":       "Total Years of Work Experience",
            "insert_after":"custom_section_experience",
        },
        {
            "fieldname":   "custom_certifications",
            "fieldtype":   "Small Text",
            "label":       "Professional Certifications",
            "insert_after":"custom_years_experience",
            "description": "e.g. ICAN, ACCA, PMP, COREN — comma separated",
        },
        {
            "fieldname":   "custom_col_exp",
            "fieldtype":   "Column Break",
            "insert_after":"custom_certifications",
        },
        {
            "fieldname":   "custom_skills",
            "fieldtype":   "Small Text",
            "label":       "Key Skills",
            "insert_after":"custom_col_exp",
            "description": "Comma-separated list of technical and soft skills",
        },
        {
            "fieldname":   "custom_current_employer",
            "fieldtype":   "Data",
            "label":       "Current / Last Employer",
            "insert_after":"custom_skills",
        },

        # ── Salary ────────────────────────────────────────────────────────
        {
            "fieldname":   "custom_section_salary",
            "fieldtype":   "Section Break",
            "label":       "Salary & Availability",
            "insert_after":"custom_current_employer",
        },
        {
            "fieldname":   "custom_salary_expectation_min",
            "fieldtype":   "Currency",
            "label":       "Minimum Salary Expectation (monthly)",
            "insert_after":"custom_section_salary",
            "description": "Enter the minimum monthly gross salary you would accept.",
        },
        {
            "fieldname":   "custom_salary_expectation_max",
            "fieldtype":   "Currency",
            "label":       "Maximum Salary Expectation (monthly)",
            "insert_after":"custom_salary_expectation_min",
        },
        {
            "fieldname":   "custom_col_salary",
            "fieldtype":   "Column Break",
            "insert_after":"custom_salary_expectation_max",
        },
        {
            "fieldname":   "custom_notice_period",
            "fieldtype":   "Select",
            "label":       "Notice Period",
            "options":     "\nImmediately available\n1 week\n2 weeks\n1 month\n2 months\n3 months",
            "insert_after":"custom_col_salary",
        },
        {
            "fieldname":   "custom_earliest_start_date",
            "fieldtype":   "Date",
            "label":       "Earliest Available Start Date",
            "insert_after":"custom_notice_period",
        },

        # ── Cover Letter & Resume ──────────────────────────────────────────
        {
            "fieldname":   "custom_section_docs",
            "fieldtype":   "Section Break",
            "label":       "Resume & Cover Letter",
            "insert_after":"custom_earliest_start_date",
        },
        {
            "fieldname":   "custom_resume_file",
            "fieldtype":   "Attach",
            "label":       "Resume / CV",
            "insert_after":"custom_section_docs",
            "description": "PDF or Word format, maximum 5MB",
        },
        {
            "fieldname":   "custom_linkedin_url",
            "fieldtype":   "Data",
            "label":       "LinkedIn Profile URL",
            "insert_after":"custom_resume_file",
        },
        {
            "fieldname":   "custom_cover_letter",
            "fieldtype":   "Text Editor",
            "label":       "Cover Letter",
            "insert_after":"custom_linkedin_url",
        },

        # ── AI Screening Results (read-only, set by system) ───────────────
        {
            "fieldname":   "custom_section_screening",
            "fieldtype":   "Section Break",
            "label":       "AI Screening Results",
            "insert_after":"custom_cover_letter",
            "read_only":   1,
        },
        {
            "fieldname":   "custom_screening_status",
            "fieldtype":   "Select",
            "label":       "Screening Decision",
            "options":     "\nShortlisted\nRefer to HR\nRejected\nNo Profile - Manual Review",
            "read_only":   1,
            "in_list_view":1,
            "bold":        1,
            "insert_after":"custom_section_screening",
        },
        {
            "fieldname":   "custom_screening_score",
            "fieldtype":   "Float",
            "label":       "Total Score (%)",
            "read_only":   1,
            "in_list_view":1,
            "insert_after":"custom_screening_status",
        },
        {
            "fieldname":   "custom_col_screening",
            "fieldtype":   "Column Break",
            "insert_after":"custom_screening_score",
        },
        {
            "fieldname":   "custom_matched_skills",
            "fieldtype":   "Small Text",
            "label":       "Matched Skills",
            "read_only":   1,
            "insert_after":"custom_col_screening",
        },
        {
            "fieldname":   "custom_missing_skills",
            "fieldtype":   "Small Text",
            "label":       "Missing Mandatory Skills",
            "read_only":   1,
            "insert_after":"custom_matched_skills",
        },
        {
            "fieldname":   "custom_score_breakdown",
            "fieldtype":   "Small Text",
            "label":       "Score Breakdown",
            "read_only":   1,
            "insert_after":"custom_missing_skills",
            "description": "Education / Degree Class / Experience / Skills / Certs / Location / Salary",
        },
        {
            "fieldname":   "custom_ai_narrative",
            "fieldtype":   "Text Editor",
            "label":       "AI Screening Narrative",
            "read_only":   1,
            "insert_after":"custom_score_breakdown",
        },
    ],

    # ── Job Opening additions ──────────────────────────────────────────────
    "Job Opening": [
        {
            "fieldname":   "closes_on",
            "fieldtype":   "Date",
            "label":       "Application Closing Date",
            "insert_after":"expected_compensation",
            "description": "Shortlist emails sent to candidates on this date.",
        },
        {
            "fieldname":   "custom_emails_dispatched",
            "fieldtype":   "Check",
            "label":       "Shortlist Emails Dispatched",
            "default":     "0",
            "read_only":   1,
            "insert_after":"closes_on",
        },
        {
            "fieldname":   "custom_send_rejection_email",
            "fieldtype":   "Check",
            "label":       "Send Rejection Emails",
            "default":     "1",
            "insert_after":"custom_emails_dispatched",
        },
    ],
}


def create_all():
    """Entry point — safe to run multiple times (idempotent)."""
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    frappe.db.commit()
    print("[Recruitment Custom Fields v2] All fields created.")