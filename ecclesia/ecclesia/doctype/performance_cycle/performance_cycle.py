# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# ecclesia/doctype/performance_cycle/performance_cycle.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, cint, nowdate, getdate, date_diff

class PerformanceCycle(Document):

    def validate(self):
        self._validate_date_order()
        self._validate_deadline_order()

    def before_save(self):
        self._compute_duration_fields()
        self._compute_progress_metrics()

    def on_submit(self):
        self.status = "Active"
        self._close_other_active_cycles()
        self._notify_all_employees()

    def on_cancel(self):
        self.status = "Cancelled"

    # ── Date validation ──────────────────────────────────────────────

    def _validate_date_order(self):
        if self.start_date and self.end_date:
            if getdate(self.end_date) <= getdate(self.start_date):
                frappe.throw(_("Cycle End Date must be after Start Date."))

    def _validate_deadline_order(self):
        if not (self.start_date and self.end_date):
            return
        start = getdate(self.start_date)
        end   = getdate(self.end_date)
        stages = [
            ("goal_setting_deadline",   "Goal Setting"),
            ("goal_approval_deadline",  "Goal Approval"),
            ("self_appraisal_deadline", "Self Appraisal"),
            ("peer_review_deadline",    "Peer Review"),
            ("manager_review_deadline", "Manager Review"),
            ("calibration_deadline",    "Calibration"),
        ]
        prev_date, prev_name = start, "Cycle Start"
        for field, label in stages:
            val = self.get(field)
            if not val:
                continue
            d = getdate(val)
            if d < start or d > end:
                frappe.throw(
                    _("{0} Deadline must fall within the cycle period ({1} to {2}).").format(
                        label, self.start_date, self.end_date))
            if d < prev_date:
                frappe.throw(
                    _("{0} Deadline must be after {1}.").format(label, prev_name))
            prev_date = d
            prev_name = label

    # ── Computed duration fields ─────────────────────────────────────

    def _compute_duration_fields(self):
        today = getdate(nowdate())
        if self.start_date and self.end_date:
            self.cycle_duration_days = date_diff(self.end_date, self.start_date)
        if self.start_date:
            elapsed = date_diff(today, self.start_date)
            self.days_elapsed = max(0, elapsed)

    # ── Progress metrics ─────────────────────────────────────────────

    def _compute_progress_metrics(self):
        if not self.company:
            return

        # Eligible employees
        employees = frappe.get_all("Employee",
            filters={"status": "Active", "company": self.company},
            fields=["name"])
        total = len(employees)
        self.employee_count = total
        self.total_employees = total
        if not total:
            return

        emp_names = [e.name for e in employees]

        # Goals
        with_goals = frappe.db.count("Performance Goal", {
            "performance_cycle": self.name,
            "owner_employee": ["in", emp_names],
            "status": ["in", ["Approved", "In Progress", "Completed"]]
        })
        # Unique employees with approved goals
        with_goals_emp = len(set(frappe.db.sql_list("""
            SELECT DISTINCT owner_employee FROM `tabPerformance Goal`
            WHERE performance_cycle=%s AND owner_employee IN ({})
              AND status IN ('Approved','In Progress','Completed')
        """.format(",".join(["%s"] * len(emp_names))),
            [self.name] + emp_names)))
        self.goal_setting_progress = round(with_goals_emp / total * 100, 1)

        # Self appraisals
        self_done = len(set(frappe.db.sql_list("""
            SELECT DISTINCT employee FROM `tabSelf Appraisal`
            WHERE performance_cycle=%s AND employee IN ({}) AND docstatus=1
        """.format(",".join(["%s"] * len(emp_names))),
            [self.name] + emp_names)))
        self.self_appraisal_progress = round(self_done / total * 100, 1)

        # Peer reviews (at least one received)
        peer_done = len(set(frappe.db.sql_list("""
            SELECT DISTINCT reviewee FROM `tabPeer Review`
            WHERE performance_cycle=%s AND reviewee IN ({}) AND docstatus=1
        """.format(",".join(["%s"] * len(emp_names))),
            [self.name] + emp_names)))
        self.peer_review_progress = round(peer_done / total * 100, 1)

        # Manager reviews
        mgr_done = len(set(frappe.db.sql_list("""
            SELECT DISTINCT employee FROM `tabManager Review 360`
            WHERE performance_cycle=%s AND employee IN ({}) AND docstatus=1
        """.format(",".join(["%s"] * len(emp_names))),
            [self.name] + emp_names)))
        self.manager_review_progress = round(mgr_done / total * 100, 1)

        # Calibration
        calib_done = frappe.db.count("Employee Performance Record", {
            "cycle": self.name,
            "calibration_status": "Calibrated",
            "employee": ["in", emp_names]
        })
        self.calibration_progress = round(calib_done / total * 100, 1)

        # Overall progress (average of all stages)
        self.overall_progress = round(
            (self.goal_setting_progress + self.self_appraisal_progress +
             self.peer_review_progress + self.manager_review_progress +
             self.calibration_progress) / 5, 1)

        # Submitted count and completion rate
        self.submitted_count = mgr_done
        self.completion_rate = round(mgr_done / total * 100, 1)

        # Score averages from EPRs
        epr_scores = frappe.db.sql("""
            SELECT composite_score, final_rating
            FROM `tabEmployee Performance Record`
            WHERE cycle=%s AND status != 'Cancelled'
              AND composite_score > 0
        """, self.name, as_dict=True)
        if epr_scores:
            self.avg_composite_score = round(
                sum(flt(r.composite_score) for r in epr_scores) / len(epr_scores), 1)
            final_scores = [flt(r.final_rating) for r in epr_scores if flt(r.final_rating) > 0]
            if final_scores:
                self.avg_final_rating = round(sum(final_scores) / len(final_scores), 1)

        # Rating distribution text
        from ecclesia.doctype.employee_performance_record.employee_performance_record import _get_band
        bands = {}
        for r in epr_scores:
            b = _get_band(flt(r.composite_score))
            bands[b] = bands.get(b, 0) + 1
        if bands:
            parts = [f"{b}: {round(v/len(epr_scores)*100)}%" for b, v in sorted(bands.items())]
            self.performance_breakdown = "  |  ".join(parts)

    # ── Notifications ────────────────────────────────────────────────

    def _close_other_active_cycles(self):
        others = frappe.get_all("Performance Cycle",
            filters={"status": "Active", "name": ("!=", self.name),
                     "company": self.company},
            fields=["name"])
        for c in others:
            frappe.db.set_value("Performance Cycle", c.name, "status", "Closed")

    def _notify_all_employees(self):
        if not self.description:
            return
        employees = frappe.get_all("Employee",
            filters={"status": "Active", "company": self.company},
            fields=["user_id", "employee_name"])
        count = 0
        for emp in employees:
            if emp.user_id:
                frappe.sendmail(
                    recipients=[emp.user_id],
                    subject=f"Performance Cycle Launched: {self.title}",
                    message=(f"<h3>{self.title}</h3>"
                             f"<p>Period: {self.start_date} to {self.end_date}</p>"
                             f"<p>{self.description}</p>"
                             + (f"<p>{self.submission_instructions}</p>"
                                if self.submission_instructions else ""))
                )
                count += 1
        frappe.msgprint(
            _(f"Launch notification sent to {count} employees."),
            indicator="green", alert=True)


@frappe.whitelist()
def refresh_cycle_analytics(docname):
    """HR-callable to recompute all cycle progress metrics."""
    doc = frappe.get_doc("Performance Cycle", docname)
    doc._compute_duration_fields()
    doc._compute_progress_metrics()
    doc.save(ignore_permissions=True)
    return {
        "goal_setting_progress":    doc.goal_setting_progress,
        "self_appraisal_progress":  doc.self_appraisal_progress,
        "peer_review_progress":     doc.peer_review_progress,
        "manager_review_progress":  doc.manager_review_progress,
        "calibration_progress":     doc.calibration_progress,
        "overall_progress":         doc.overall_progress,
        "completion_rate":          doc.completion_rate,
        "avg_composite_score":      doc.avg_composite_score,
        "performance_breakdown":    doc.performance_breakdown,
    }