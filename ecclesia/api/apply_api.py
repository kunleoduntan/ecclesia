# ecclesia/api/apply_api.py
import frappe
from frappe import _
from frappe.utils import nowdate, cint, flt


@frappe.whitelist(allow_guest=True)
def get_open_jobs():
    """
    Return all open Job Openings.
    Reads ec_* custom fields that exist on tabJob Opening.
    """
    # ── Step 1: get standard fields first ─────────────────────────
    jobs = frappe.get_all(
        "Job Opening",
        filters={"status": "Open"},
        fields=[
            "name", "job_title", "department", "location",
            "employment_type", "closes_on", "description",
            "company", "status",
        ],
        order_by="creation desc",
        limit=100
    )

    if not jobs:
        return []

    # ── Step 2: find which ec_* fields actually exist on tabJob Opening ──
    EC_FIELDS = [
        "ec_experience_years_min",
        "ec_experience_years_max",
        "ec_required_certifications",
        "ec_nice_to_have_skills",
        "ec_required_location_city",
        "ec_required_languages",
        "ec_min_stability_years",
        "ec_required_industry",
    ]
    existing_cols = set(
        r[0] for r in frappe.db.sql(
            "SHOW COLUMNS FROM `tabJob Opening`"
        )
    )
    ec_available = [f for f in EC_FIELDS if f in existing_cols]

    # ── Step 3: bulk-fetch ec_* fields in one SQL call ─────────────
    ec_map = {}
    if ec_available:
        names = [j["name"] for j in jobs]
        placeholders = ",".join(["%s"] * len(names))
        cols = ", ".join(["`" + f + "`" for f in ec_available])
        rows = frappe.db.sql(
            "SELECT `name`, {} FROM `tabJob Opening` WHERE `name` IN ({})".format(
                cols, placeholders
            ),
            names, as_dict=True
        )
        for r in rows:
            ec_map[r["name"]] = r

    # ── Step 4: also try Job Requirement Profile (gracefully) ───────
    jrp_map = {}
    try:
        if frappe.db.table_exists("tabJob Requirement Profile"):
            # Discover which fields actually exist on Job Requirement Profile
            jrp_cols = set(
                r[0] for r in frappe.db.sql(
                    "SHOW COLUMNS FROM `tabJob Requirement Profile`"
                )
            )
            # Build the select list from only existing fields
            wanted = {
                "ec_experience_years_min": "ec_experience_years_min",
                "minimum_experience":      "minimum_experience",
                "min_experience":          "min_experience",
                "ec_min_degree_class":     "ec_min_degree_class",
                "minimum_degree_class":    "minimum_degree_class",
                "min_degree_class":        "min_degree_class",
                "ec_min_education":        "ec_min_education",
                "minimum_education":       "minimum_education",
                "ec_required_skills":      "ec_required_skills",
                "required_skills":         "required_skills",
            }
            sel_fields = ["name", "job_opening"]
            for col in wanted:
                if col in jrp_cols:
                    sel_fields.append(col)

            if len(sel_fields) > 2:
                job_names = [j["name"] for j in jobs]
                ph = ",".join(["%s"] * len(job_names))
                cols_sql = ", ".join(["`" + f + "`" for f in sel_fields])
                jrp_rows = frappe.db.sql(
                    "SELECT {} FROM `tabJob Requirement Profile` "
                    "WHERE `job_opening` IN ({})".format(cols_sql, ph),
                    job_names, as_dict=True
                )
                for r in jrp_rows:
                    jrp_map[r.get("job_opening")] = r
    except Exception:
        pass  # Job Requirement Profile missing or wrong — not critical

    # ── Step 5: assemble result ─────────────────────────────────────
    result = []
    for job in jobs:
        name = job["name"]
        ec   = ec_map.get(name, {})
        jrp  = jrp_map.get(name, {})

        # Description preview
        desc_plain = frappe.utils.strip_html(job.get("description") or "")
        job["description_preview"] = (
            desc_plain[:200] + "…" if len(desc_plain) > 200 else desc_plain
        )

        # Work mode — try multiple possible field names
        job["work_mode"] = (
            ec.get("ec_work_mode") or
            ec.get("custom_work_mode") or
            job.get("work_arrangement") or
            ""
        )

        # Requirements — try ec_* first, then JRP, then nothing
        job["min_experience"] = (
            ec.get("ec_experience_years_min") or
            jrp.get("ec_experience_years_min") or
            jrp.get("minimum_experience") or
            jrp.get("min_experience") or
            ""
        )
        job["min_education"] = (
            jrp.get("ec_min_education") or
            jrp.get("minimum_education") or
            ""
        )
        job["min_degree_class"] = (
            jrp.get("ec_min_degree_class") or
            jrp.get("minimum_degree_class") or
            jrp.get("min_degree_class") or
            ""
        )
        job["required_certifications"] = (
            ec.get("ec_required_certifications") or
            jrp.get("ec_required_certifications") or
            ""
        )
        job["required_location"] = (
            ec.get("ec_required_location_city") or
            jrp.get("ec_required_location_city") or
            ""
        )

        # Skills — try to get from JRP child table
        job["skills"] = _get_skills(name, jrp)

        result.append(job)

    return result


def _get_skills(job_opening_name, jrp):
    """
    Try to load skills from the Job Requirement Profile child table.
    Returns list of {skill, mandatory} or empty list if nothing found.
    """
    try:
        # Try the child table we defined: Job Requirement Skill
        if frappe.db.table_exists("tabJob Requirement Skill"):
            rows = frappe.db.sql("""
                SELECT s.skill, s.mandatory
                FROM `tabJob Requirement Skill` s
                JOIN `tabJob Requirement Profile` p ON s.parent = p.name
                WHERE p.job_opening = %s
                ORDER BY s.mandatory DESC, s.idx ASC
                LIMIT 20
            """, job_opening_name, as_dict=True)
            if rows:
                return [{"skill": r.skill, "mandatory": bool(r.mandatory)}
                        for r in rows if r.skill]

        # Fallback: parse text field from JRP
        import json
        raw = (jrp.get("required_skills") or
               jrp.get("ec_required_skills") or "")
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                # Plain text — split by comma/newline
                items = [s.strip() for s in raw.replace("\n", ",").split(",")
                         if s.strip()]
                return [{"skill": s, "mandatory": True} for s in items[:10]]
    except Exception:
        pass
    return []


@frappe.whitelist(allow_guest=True)
def submit_application(
    job_opening,
    applicant_name,
    email_id,
    mobile_no            = "",
    cover_letter         = "",
    gender               = "",
    location_city        = "",
    location_state       = "",
    willing_to_relocate  = 0,
    work_mode            = "",
    highest_qualification= "",
    degree_class         = "",
    years_experience     = 0,
    skills               = "",
    certifications       = "",
    salary_expectation   = 0,
    notice_period        = "",
):
    if not job_opening:
        frappe.throw(_("Job Opening is required."), frappe.ValidationError)
    if not applicant_name:
        frappe.throw(_("Your name is required."), frappe.ValidationError)
    if not email_id:
        frappe.throw(_("Email address is required."), frappe.ValidationError)

    status = frappe.db.get_value("Job Opening", job_opening, "status")
    if status and status != "Open":
        frappe.throw(
            _("This position is no longer accepting applications."),
            frappe.ValidationError
        )

    if frappe.db.exists("Job Applicant",
                        {"email_id": email_id, "job_opening": job_opening}):
        return {
            "success": False,
            "message": "You have already applied for this role. "
                       "We will be in touch after the closing date."
        }

    # Base fields — always exist in ERPNext
    doc_data = {
        "doctype":        "Job Applicant",
        "job_opening":    job_opening,
        "applicant_name": applicant_name,
        "email_id":       email_id,
        "mobile_no":      mobile_no,
        "cover_letter":   cover_letter,
        "status":         "Open",
    }

    # Custom fields — only set ones that actually exist
    custom_candidates = {
        "custom_gender":                gender,
        "custom_location_city":         location_city,
        "custom_location_state":        location_state,
        "custom_willing_to_relocate":   cint(willing_to_relocate),
        "custom_preferred_work_mode":   work_mode,
        "custom_highest_qualification": highest_qualification,
        "custom_degree_class":          degree_class,
        "custom_years_experience":      flt(years_experience),
        "custom_skills":                skills,
        "custom_certifications":        certifications,
        "custom_salary_expectation":    flt(salary_expectation),
        "custom_notice_period":         notice_period,
    }
    existing_custom = set(
        r[0] for r in frappe.db.sql(
            "SELECT fieldname FROM `tabCustom Field` WHERE dt = 'Job Applicant'"
        )
    )
    for field, value in custom_candidates.items():
        if field in existing_custom:
            doc_data[field] = value

    doc = frappe.get_doc(doc_data)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    _send_acknowledgement(doc, job_opening)

    return {"success": True, "applicant": doc.name,
            "message": "Application received successfully."}


def _send_acknowledgement(doc, job_opening):
    try:
        job_data  = frappe.db.get_value(
            "Job Opening", job_opening,
            ["job_title", "closes_on", "company"], as_dict=True
        ) or {}
        company   = (job_data.get("company") or
                     frappe.defaults.get_global_default("company") or "")
        job_title = job_data.get("job_title") or "the role"
        closes_on = str(job_data.get("closes_on") or "")
        closes_note = (
            " We will review all applications after <strong>{}</strong> "
            "and contact shortlisted candidates.".format(closes_on)
            if closes_on else
            " We will review your application and be in touch shortly."
        )
        frappe.sendmail(
            recipients=[doc.email_id],
            subject="Application Received — {} at {}".format(job_title, company),
            message=(
                "<p>Dear {},</p>"
                "<p>Thank you for applying for <strong>{}</strong> "
                "at <strong>{}</strong>.</p>"
                "<p>We have received your application.{}</p>"
                "<p>Best regards,<br><strong>HR Team</strong><br>{}</p>"
            ).format(doc.applicant_name, job_title, company, closes_note, company)
        )
    except Exception:
        frappe.log_error(
            frappe.get_traceback(), "Apply Acknowledgement Email Error"
        )