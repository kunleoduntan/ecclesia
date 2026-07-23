# ecclesia/report/diversity_report/diversity_report.py
import frappe, json
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    return get_columns(), get_data(filters or {})


def get_columns():
    return [
        {"label":_("Job Opening"),         "fieldname":"job_opening",    "fieldtype":"Link",
         "options":"Job Opening",           "width":150},
        {"label":_("Job Title"),           "fieldname":"job_title",      "fieldtype":"Data",    "width":180},
        {"label":_("Total Applied"),       "fieldname":"total",          "fieldtype":"Int",     "width":100},
        {"label":_("Male Applied"),        "fieldname":"male_applied",   "fieldtype":"Int",     "width":100},
        {"label":_("Female Applied"),      "fieldname":"female_applied", "fieldtype":"Int",     "width":110},
        {"label":_("Other / DNS"),         "fieldname":"other_applied",  "fieldtype":"Int",     "width":100},
        {"label":_("Total Shortlisted"),   "fieldname":"total_short",    "fieldtype":"Int",     "width":130},
        {"label":_("Male Shortlisted"),    "fieldname":"male_short",     "fieldtype":"Int",     "width":120},
        {"label":_("Female Shortlisted"),  "fieldname":"female_short",   "fieldtype":"Int",     "width":135},
        {"label":_("Female Apply %"),      "fieldname":"female_apply_pct","fieldtype":"Float",  "width":120},
        {"label":_("Female Shortlist %"),  "fieldname":"female_short_pct","fieldtype":"Float",  "width":135},
        {"label":_("Equity Gap"),          "fieldname":"equity_gap",     "fieldtype":"Data",    "width":120},
    ]


def get_data(filters):
    job_opening = filters.get("job_opening")
    cond = "jo.status != 'Cancelled'"
    params = {}
    if job_opening:
        cond += " AND jo.name = %(job_opening)s"
        params["job_opening"] = job_opening

    openings = frappe.db.sql(f"""
        SELECT jo.name, jo.job_title
        FROM `tabJob Opening` jo WHERE {cond}
        ORDER BY jo.creation DESC LIMIT 50
    """, params, as_dict=True)

    rows = []
    for jop in openings:
        applicants = frappe.db.sql("""
            SELECT ja.custom_gender, rsr.auto_decision, rsr.hr_override
            FROM `tabJob Applicant` ja
            LEFT JOIN `tabResume Screening Result` rsr
                ON rsr.job_opening = ja.job_opening
               AND rsr.candidate_name = ja.applicant_name
            WHERE ja.job_opening = %s
        """, jop.name, as_dict=True)

        total = len(applicants)
        if not total:
            continue

        def gc(gender, lst):
            return sum(1 for a in lst
                       if (a.custom_gender or "").lower() == gender.lower())
        def gsh(gender):
            return sum(1 for a in applicants
                       if (a.custom_gender or "").lower() == gender.lower()
                       and (a.hr_override or a.auto_decision) == "Shortlisted")

        ma = gc("Male",   applicants)
        fa = gc("Female", applicants)
        oa = total - ma - fa
        ts = sum(1 for a in applicants if (a.hr_override or a.auto_decision) == "Shortlisted")
        ms = gsh("Male")
        fs = gsh("Female")

        fap = round(fa / max(1, total) * 100, 1)
        fsp = round(fs / max(1, ts)    * 100, 1) if ts else 0
        gap = fsp - fap

        if abs(gap) < 5:
            equity = "✅ Equitable"
        elif gap < 0:
            equity = f"⚠️ Under ({gap:.1f}%)"
        else:
            equity = f"↑ Over (+{gap:.1f}%)"

        rows.append({
            "job_opening":     jop.name,
            "job_title":       jop.job_title,
            "total":           total,
            "male_applied":    ma,
            "female_applied":  fa,
            "other_applied":   oa,
            "total_short":     ts,
            "male_short":      ms,
            "female_short":    fs,
            "female_apply_pct":fap,
            "female_short_pct":fsp,
            "equity_gap":      equity,
        })
    return rows


@frappe.whitelist()
def download_excel(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    from ecclesia.report.excel_utils import EcclesiaReport
    columns = get_columns()
    data    = get_data(filters or {})
    report  = EcclesiaReport(
        "Diversity Report", filters or {}, columns, data,
        subtitle="Gender breakdown · Applicants vs Shortlisted"
    )
    if len(data) > 1:
        report.add_bar_chart(
            "Gender Distribution per Role",
            cat_col_idx=2,
            val_col_idxes=[4, 5, 8, 9],
            sheet_title="Diversity Chart",
            legend_titles=["Male Applied","Female Applied",
                           "Male Shortlisted","Female Shortlisted"]
        )
    return report.to_response("Diversity_Report.xlsx")
