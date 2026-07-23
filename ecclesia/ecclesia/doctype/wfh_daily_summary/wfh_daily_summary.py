"""
WFH Daily Summary Controller
Ecclesia Module – ERPNext

Validates the daily declaration, computes composite score,
flags anomalies, and integrates with session + activity data.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt, time_diff_in_hours


class WFHDailySummary(Document):

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    def before_save(self):
        self._enforce_session_exists()
        self._pull_session_hours()
        self._pull_activity_scores()
        self._calc_consistency_score()
        self._calc_composite_score()
        self._detect_flags()

    def validate(self):
        self._validate_no_future_date()
        self._check_duplicate()

    def on_submit(self):
        self.status = "Submitted"
        self.db_update()
        frappe.db.commit()

    # ─── Private Helpers ──────────────────────────────────────────────────────

    def _enforce_session_exists(self):
        """Summary requires a linked session."""
        if not self.session:
            frappe.throw(
                _("A WFH Session is required before submitting the Daily Summary. "
                  "Please check in first.")
            )
        session_status = frappe.db.get_value("WFH Session", self.session, "status")
        if session_status == "Open":
            frappe.msgprint(
                _("Your WFH Session is still open. Remember to check out."),
                indicator="orange",
                alert=True,
            )

    def _pull_session_hours(self):
        if self.session:
            hours = frappe.db.get_value("WFH Session", self.session, "total_hours") or 0
            self.hours_logged = flt(hours, 2)

    def _pull_activity_scores(self):
        """Aggregate points and business value from Work Activity Logs."""
        if not (self.employee and self.date):
            return
        result = frappe.db.sql(
            """
            SELECT
                COALESCE(SUM(points), 0)          AS total_points,
                COALESCE(SUM(business_value), 0)  AS total_value
            FROM `tabWork Activity Log`
            WHERE employee = %s
              AND date      = %s
            """,
            (self.employee, self.date),
            as_dict=True,
        )
        if result:
            self.activity_score  = flt(result[0].total_points, 2)
            self.value_generated = flt(result[0].total_value, 2)

    def _calc_consistency_score(self):
        """Rolling 7-day streak of submitted summaries (0–10 scale)."""
        if not (self.employee and self.date):
            return
        submitted_days = frappe.db.sql(
            """
            SELECT COUNT(*) as cnt
            FROM `tabWFH Daily Summary`
            WHERE employee = %s
              AND date      BETWEEN DATE_SUB(%s, INTERVAL 7 DAY) AND %s
              AND status   IN ('Submitted', 'Reviewed')
              AND docstatus = 1
            """,
            (self.employee, self.date, self.date),
        )[0][0]
        self.consistency_score = round((submitted_days / 7) * 10, 2)

    def _calc_composite_score(self):
        """
        Composite = 50% activity_score (capped 100) + 30% hours_score + 20% self_rating_score
        All components normalised to 0–100.
        """
        # Activity: cap at 200 pts → normalize to 100
        max_activity = 200
        activity_norm = min(flt(self.activity_score, 2), max_activity) / max_activity * 100

        # Hours: 8 hrs = 100
        max_hours = 8
        hours_norm = min(flt(self.hours_logged, 2), max_hours) / max_hours * 100

        # Self rating: 1–5 → 20–100
        rating = flt(self.self_rating or 0)
        rating_norm = (rating / 5) * 100

        self.composite_score = round(
            (activity_norm * 0.50) + (hours_norm * 0.30) + (rating_norm * 0.20),
            2,
        )

    def _detect_flags(self):
        flags = []
        # Inactivity from session
        if self.session:
            inactivity = frappe.db.get_value(
                "WFH Session", self.session, "inactivity_flag"
            )
            if inactivity:
                self.has_inactivity_flag = 1
                flags.append("Session was flagged for inactivity (>3 hrs no activity).")

        # High hours, low output
        if flt(self.hours_logged) >= 6 and flt(self.activity_score) < 5:
            flags.append("High hours logged but very low activity score (<5 pts).")

        # No activity at all
        if flt(self.activity_score) == 0 and flt(self.hours_logged) > 0:
            flags.append("Hours logged but zero activity recorded.")

        if flags:
            self.status = "Flagged"
            self.flag_notes = "\n".join(flags)
        else:
            self.has_inactivity_flag = 0
            if self.status == "Flagged":
                self.status = "Draft"
            self.flag_notes = ""

    def _validate_no_future_date(self):
        if self.date and getdate(self.date) > getdate(nowdate()):
            frappe.throw(_("Cannot submit a Daily Summary for a future date."))

    def _check_duplicate(self):
        filters = {
            "employee": self.employee,
            "date": self.date,
            "docstatus": ("!=", 2),
        }
        if not self.is_new():
            filters["name"] = ("!=", self.name)
        if frappe.db.exists("WFH Daily Summary", filters):
            frappe.throw(
                _("A Daily Summary already exists for {0} on {1}.").format(
                    self.employee_name or self.employee, self.date
                )
            )


# ─── Scheduler & Reminders ────────────────────────────────────────────────────

def send_summary_reminders():
    """
    Scheduler: daily at 17:00.
    Email employees on WFH today who haven't submitted a summary.
    """
    today = nowdate()
    # Find employees with an open/closed session but no summary
    missing = frappe.db.sql(
        """
        SELECT s.employee, s.employee_name, e.user_id
        FROM `tabWFH Session` s
        JOIN `tabEmployee` e ON e.name = s.employee
        WHERE s.date = %s
          AND s.docstatus != 2
          AND NOT EXISTS (
              SELECT 1 FROM `tabWFH Daily Summary` d
              WHERE d.employee = s.employee
                AND d.date     = %s
                AND d.docstatus != 2
          )
        """,
        (today, today),
        as_dict=True,
    )
    for row in missing:
        if not row.user_id:
            continue
        frappe.sendmail(
            recipients=[row.user_id],
            subject=f"[Reminder] Please submit your WFH Daily Summary for {today}",
            message=(
                f"Hi <b>{row.employee_name}</b>,<br><br>"
                f"You have an active WFH Session today but haven't submitted your "
                f"Daily Summary yet. It only takes 30–60 seconds!<br><br>"
                f"Please log in and submit before end of day."
            ),
        )
