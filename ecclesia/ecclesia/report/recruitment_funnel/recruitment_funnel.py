# ecclesia/report/recruitment_funnel/recruitment_funnel.py
import frappe, json
from frappe import _
from frappe.utils import flt, date_diff, nowdate, getdate


def execute(filters=None):
    return get_columns(), get_data(filters or {})


def get_columns():
    return [
        {"label":_("Job Opening"),     "fieldname":"job_opening",   "fieldtype":"Link",
         "options":"Job Opening",      "width":150},
        {"label":_("Job Title"),       "fieldname":"job_title",     "fieldtype":"Data",    "width":180},
        {"label":_("Applied"),         "fieldname":"applied",       "fieldtype":"Int",     "width":80},
        {"label":_("Screened"),        "fieldname":"screened",      "fieldtype":"Int",     "width":80},
        {"label":_("Shortlisted"),     "fieldname":"shortlisted",   "fieldtype":"Int",     "width":100},
        {"label":_("Refer to HR"),     "fieldname":"referred",      "fieldtype":"Int",     "width":100},
        {"label":_("Rejected"),        "fieldname":"rejected",      "fieldtype":"Int",     "width":85},
        {"label":_("Shortlist %"),     "fieldname":"shortlist_pct", "fieldtype":"Float",   "width":100},
        {"label":_("Avg Score (%)"),   "fieldname":"avg_score",     "fieldtype":"Float",   "width":110},
        {"label":_("Top Score (%)"),   "fieldname":"top_score",     "fieldtype":"Float",   "width":110},
        {"label":_("Closing Date"),    "fieldname":"closes_on",     "fieldtype":"Date",    "width":110},
        {"label":_("Days Open"),       "fieldname":"days_open",     "fieldtype":"Int",     "width":90},
        {"label":_("Emails Sent"),     "fieldname":"emails_sent",   "fieldtype":"Data",    "width":100},
    ]


def get_data(filters):
    job_opening = filters.get("job_opening")
    from_date   = filters.get("from_date")
    to_date     = filters.get("to_date")

    conds  = "jo.status != 'Cancelled'"
    params = {}
    if job_opening:
        conds += " AND jo.name = %(job_opening)s"
        params["job_opening"] = job_opening
    if from_date:
        conds += " AND jo.creation >= %(from_date)s"
        params["from_date"] = from_date
    if to_date:
        conds += " AND jo.creation <= %(to_date)s"
        params["to_date"] = to_date

    openings = frappe.db.sql(f"""
        SELECT jo.name, jo.job_title, jo.closes_on, jo.creation,
               IFNULL(jo.custom_emails_dispatched, 0) AS emails_dispatched
        FROM `tabJob Opening` jo
        WHERE {conds}
        ORDER BY jo.creation DESC LIMIT 100
    """, params, as_dict=True)

    today = getdate(nowdate())
    rows  = []
    for jop in openings:
        results = frappe.get_all("Resume Screening Result",
            filters={"job_opening": jop.name},
            fields=["auto_decision","hr_override","total_score"])

        applied  = frappe.db.count("Job Applicant", {"job_opening": jop.name})
        screened = len(results)
        scores   = [flt(r.total_score) for r in results]
        decisions = [r.hr_override or r.auto_decision for r in results]

        short = decisions.count("Shortlisted")
        ref   = decisions.count("Refer to HR")
        rej   = decisions.count("Rejected")

        rows.append({
            "job_opening":  jop.name,
            "job_title":    jop.job_title,
            "applied":      applied,
            "screened":     screened,
            "shortlisted":  short,
            "referred":     ref,
            "rejected":     rej,
            "shortlist_pct":round(short / max(1, screened) * 100, 1),
            "avg_score":    round(sum(scores) / max(1, len(scores)), 1) if scores else 0,
            "top_score":    round(max(scores), 1) if scores else 0,
            "closes_on":    jop.closes_on,
            "days_open":    date_diff(today, getdate(jop.creation)) if jop.creation else 0,
            "emails_sent":  "✅ Yes" if jop.emails_dispatched else "⏳ No",
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
        "Recruitment Funnel Report", filters or {}, columns, data,
        subtitle="Application → Screened → Shortlisted → Rejected conversion"
    )
    if len(data) > 1:
        report.add_bar_chart(
            "Recruitment Funnel",
            cat_col_idx=2,
            val_col_idxes=[3, 4, 5, 7],
            sheet_title="Funnel Chart",
            legend_titles=["Applied", "Screened", "Shortlisted", "Rejected"]
        )
    return report.to_response("Recruitment_Funnel.xlsx")
