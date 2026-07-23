# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# ecclesia/doctype/employee_performance_record/employee_performance_record.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, cint, nowdate, getdate

BAND_MAP = [
    (90, "Outstanding"),
    (75, "Exceeds Expectations"),
    (60, "Meets Expectations"),
    (40, "Needs Improvement"),
    (0,  "Unsatisfactory"),
]

def _get_band(score):
    for threshold, label in BAND_MAP:
        if flt(score) >= threshold:
            return label
    return "Unsatisfactory"


class EmployeePerformanceRecord(Document):

    def validate(self):
        self._check_duplicate()

    def before_save(self):
        self._compute_composite_score()
        self._apply_performance_band()
        self._compute_analytics()
        self._update_dashboard_fields()

    # ── Duplicate guard ──────────────────────────────────────────────

    def _check_duplicate(self):
        existing = frappe.db.get_value("Employee Performance Record",
            {"employee": self.employee, "cycle": self.cycle,
             "name": ("!=", self.name)}, "name")
        if existing:
            frappe.throw(
                _("A performance record for {0} in cycle {1} already exists: {2}").format(
                    self.employee, self.cycle, existing))

    # ── Composite score ──────────────────────────────────────────────

    def _compute_composite_score(self):
        if not self.cycle:
            return
        config = frappe.db.get_value("Performance Weight Config",
            {"performance_cycle": self.cycle},
            ["goal_weight", "self_weight", "peer_weight", "manager_weight"],
            as_dict=True)
        if not config:
            return
        goal_pct    = flt(self.kpi_score)
        gw          = flt(config.goal_weight) / 100
        rev_total   = (flt(config.self_weight) + flt(config.peer_weight)
                       + flt(config.manager_weight))
        if rev_total > 0:
            rev_avg = (
                flt(self.self_score)    * flt(config.self_weight) +
                flt(self.peer_score)    * flt(config.peer_weight) +
                flt(self.manager_score) * flt(config.manager_weight)
            ) / rev_total
        else:
            rev_avg = 0
        composite = (goal_pct * gw) + ((rev_avg / 5 * 100) * (1 - gw))
        self.composite_score = round(composite, 1)

    # ── Performance band ─────────────────────────────────────────────

    def _apply_performance_band(self):
        score = flt(self.final_rating or self.calibrated_rating or self.composite_score)
        self.performance_band = _get_band(score)

    # ── Analytics ────────────────────────────────────────────────────

    def _compute_analytics(self):
        if not (self.employee and self.cycle):
            return
        dept = frappe.db.get_value("Employee", self.employee, "department") or ""

        all_eprs = frappe.db.sql("""
            SELECT epr.employee, epr.composite_score, emp.department
            FROM `tabEmployee Performance Record` epr
            JOIN `tabEmployee` emp ON emp.name = epr.employee
            WHERE epr.cycle = %s AND epr.status != 'Cancelled'
              AND epr.composite_score IS NOT NULL AND epr.composite_score > 0
        """, self.cycle, as_dict=True)

        scores_all  = [flt(r.composite_score) for r in all_eprs]
        scores_dept = [flt(r.composite_score) for r in all_eprs
                       if r.department == dept]
        my_score    = flt(self.composite_score)

        self.cycle_avg_score = round(sum(scores_all) / max(1, len(scores_all)), 1)
        self.dept_avg_score  = (round(sum(scores_dept) / len(scores_dept), 1)
                                if scores_dept else 0)
        self.score_variance  = round(my_score - self.cycle_avg_score, 1)

        sorted_dept = sorted(scores_dept, reverse=True)
        try:
            self.rank_in_dept = sorted_dept.index(my_score) + 1
        except ValueError:
            self.rank_in_dept = len(sorted_dept)

        below = sum(1 for s in scores_all if s < my_score)
        self.percentile_rank = round(below / max(1, len(scores_all)) * 100, 1)
        self.performance_trend = self._build_trend()

    def _build_trend(self):
        past = frappe.db.sql("""
            SELECT epr.composite_score, pc.end_date
            FROM `tabEmployee Performance Record` epr
            JOIN `tabPerformance Cycle` pc ON pc.name = epr.cycle
            WHERE epr.employee = %s AND epr.cycle != %s
              AND epr.composite_score > 0
            ORDER BY pc.end_date DESC LIMIT 3
        """, (self.employee, self.cycle), as_dict=True)

        if not past:
            return f"First cycle — {flt(self.composite_score):.0f}%"

        history = list(reversed(past))
        parts   = []
        for i, r in enumerate(history):
            s     = flt(r.composite_score)
            arrow = ""
            if i > 0:
                prev = flt(history[i-1].composite_score)
                arrow = "📈 " if s > prev else ("📉 " if s < prev else "➡️ ")
            parts.append(f"{arrow}{s:.0f}%")

        prev_score = flt(past[0].composite_score)
        curr       = flt(self.composite_score)
        curr_arrow = "📈 " if curr > prev_score else ("📉 " if curr < prev_score else "➡️ ")
        parts.append(f"{curr_arrow}{curr:.0f}% (current)")
        return "  →  ".join(parts)

    # ── Dashboard field values ────────────────────────────────────────

    def _update_dashboard_fields(self):
        emp_name = (frappe.db.get_value("Employee", self.employee, "employee_name")
                    or self.employee)
        self.dashboard_summary = (
            f"{emp_name}  |  Cycle: {self.cycle}  |  Status: {self.status}")
        kpi = flt(self.kpi_score)
        self.dashboard_kpi = (
            f"{kpi:.1f}% of goals met"
            + (" ✅" if kpi >= 80 else " ⚠️" if kpi >= 60 else " 🔴"))
        comp  = flt(self.composite_score)
        final = flt(self.final_rating)
        self.dashboard_rating = (
            f"Composite: {comp:.1f}%"
            + (f"  |  Final: {final:.1f}%" if final else "  |  Final: Pending"))

    # ── Release ──────────────────────────────────────────────────────

    def release_to_employee(self):
        self.status = "Released"
        self.final_submission_date = nowdate()
        self.save(ignore_permissions=True)
        emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
        emp_name = frappe.db.get_value("Employee", self.employee, "employee_name")
        if emp_user:
            score = flt(self.final_rating or self.composite_score)
            frappe.sendmail(
                recipients=[emp_user],
                subject="Your Performance Results are Ready",
                message=(
                    f"Dear {emp_name},<br><br>"
                    f"Your performance results for <b>{self.cycle}</b> are now available.<br>"
                    f"Score: <b>{score:.1f}%</b> — <b>{self.performance_band}</b><br><br>"
                    f"Log in to the Performance Hub to view your full feedback."
                )
            )


@frappe.whitelist()
def refresh_analytics(docname):
    """Called by JS Refresh button — recomputes all analytics."""
    doc = frappe.get_doc("Employee Performance Record", docname)
    doc._compute_composite_score()
    doc._apply_performance_band()
    doc._compute_analytics()
    doc._update_dashboard_fields()
    doc.save(ignore_permissions=True)
    return {
        "composite_score":   doc.composite_score,
        "performance_band":  doc.performance_band,
        "rank_in_dept":      doc.rank_in_dept,
        "percentile_rank":   doc.percentile_rank,
        "dept_avg_score":    doc.dept_avg_score,
        "cycle_avg_score":   doc.cycle_avg_score,
        "score_variance":    doc.score_variance,
        "performance_trend": doc.performance_trend,
    }