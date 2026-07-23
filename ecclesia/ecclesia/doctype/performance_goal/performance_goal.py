# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# ecclesia/doctype/performance_goal/performance_goal.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, cint, nowdate, getdate, date_diff

class PerformanceGoal(Document):

    def validate(self):
        self._validate_weight()
        self._validate_progress()
        self._validate_due_date()

    def before_save(self):
        self._update_computed_fields()
        self._compute_analytics()
        self._update_status_from_progress()
        self.last_update_date = nowdate()

    def after_insert(self):
        self.status = "Pending Approval"
        self.created_on = nowdate()
        self._notify_manager()

    def on_update(self):
        self._check_total_weight_for_cycle()

    # ── Validation ───────────────────────────────────────────────────

    def _validate_weight(self):
        if flt(self.weight) <= 0:
            frappe.throw(_("Goal weight must be greater than 0."))
        if flt(self.weight) > 100:
            frappe.throw(_("Goal weight cannot exceed 100%."))

    def _validate_progress(self):
        p = flt(self.progress)
        if p < 0 or p > 100:
            frappe.throw(_("Progress must be between 0 and 100."))

    def _validate_due_date(self):
        if self.due_date and self.performance_cycle:
            cycle_end = frappe.db.get_value("Performance Cycle",
                self.performance_cycle, "end_date")
            if cycle_end and getdate(self.due_date) > getdate(cycle_end):
                frappe.msgprint(
                    _("Goal due date ({0}) is after the cycle end date ({1}).").format(
                        self.due_date, cycle_end),
                    indicator="orange", alert=True)

    # ── Core computed fields ─────────────────────────────────────────

    def _update_computed_fields(self):
        today = getdate(nowdate())
        if self.due_date:
            self.days_remaining = max(0, date_diff(self.due_date, today))
        progress = flt(self.progress)

        # Progress band
        if   progress >= 100: self.progress_band = "100%: Complete"
        elif progress >= 76:  self.progress_band = "76-99%: Almost Done"
        elif progress >= 51:  self.progress_band = "51-75%: Well Progressed"
        elif progress >= 26:  self.progress_band = "26-50%: Halfway"
        else:                 self.progress_band = "0-25%: Just Started"

        # Progress velocity (% per day since creation)
        if self.created_on:
            days_since = date_diff(today, self.created_on)
            if days_since > 0:
                self.progress_velocity = round(progress / days_since, 2)
                # Estimated completion date
                if progress > 0 and self.progress_velocity > 0:
                    days_to_complete = (100 - progress) / self.progress_velocity
                    from frappe.utils import add_days
                    self.estimated_completion = add_days(
                        today, int(days_to_complete))

        # Update count
        self.total_updates = cint(self.total_updates or 0) + (
            1 if self.has_value_changed("progress") else 0)

    def _update_status_from_progress(self):
        progress = flt(self.progress)
        days_left = cint(self.days_remaining or 0)

        if progress >= 100:
            self.status = "Completed"
            self.progress_status = "Completed"
            self.goal_health = "Completed"
            return

        # Health assessment
        if self.status in ("Approved", "In Progress"):
            if progress >= 80:
                self.goal_health = "Healthy"
            elif days_left <= 7 and progress < 60:
                self.goal_health = "Critical"
            elif days_left <= 14 and progress < 50:
                self.goal_health = "At Risk"
            else:
                self.goal_health = "Healthy"

            # Progress status
            if days_left <= 0 and progress < 100:
                self.progress_status = "Behind Schedule"
            elif days_left <= 7 and progress < 80:
                self.progress_status = "At Risk"
            elif progress > 0:
                self.progress_status = "On Track"
            else:
                self.progress_status = "Not Started"

            # Risk factors
            risks = []
            if days_left <= 7 and progress < 80:
                risks.append("Less than 7 days remaining with <80% progress")
            if progress == 0 and days_left < (self.days_remaining or 999):
                risks.append("No progress logged yet")
            if not self.evidence_upload and progress >= 80:
                risks.append("No evidence uploaded despite high progress")
            self.risk_factors = "; ".join(risks) if risks else ""

    # ── Analytics ────────────────────────────────────────────────────

    def _compute_analytics(self):
        if not (self.owner_employee and self.performance_cycle):
            return
        dept = frappe.db.get_value("Employee", self.owner_employee, "department") or ""
        if not dept:
            return

        # Department peers in same cycle
        dept_emps = frappe.db.sql_list("""
            SELECT name FROM `tabEmployee`
            WHERE department=%s AND status='Active' AND name != %s
        """, (dept, self.owner_employee))

        if dept_emps:
            dept_goals = frappe.db.sql("""
                SELECT AVG(progress) AS avg_progress,
                       AVG(CASE WHEN progress > 0 THEN progress END) AS avg_achievement
                FROM `tabPerformance Goal`
                WHERE performance_cycle=%s AND owner_employee IN ({})
                  AND status NOT IN ('Cancelled')
            """.format(",".join(["%s"] * len(dept_emps))),
                [self.performance_cycle] + dept_emps, as_dict=True)
            if dept_goals:
                self.dept_avg_progress     = round(flt(dept_goals[0].avg_progress), 1)
                self.dept_avg_achievement  = round(flt(dept_goals[0].avg_achievement), 1)

        # Goal achievement rate = progress (since target is 100%)
        self.goal_achievement_rate = flt(self.progress)
        if self.target_value and self.current_achievement:
            # Try numeric comparison if both are numeric
            try:
                target  = float(str(self.target_value).replace(",","").replace("%",""))
                current = float(str(self.current_achievement).replace(",","").replace("%",""))
                self.goal_achievement_rate = round(current / max(1, target) * 100, 1)
                diff = current - target
                self.variance_from_target = (
                    f"+{diff:.1f} ahead" if diff > 0
                    else f"{diff:.1f} behind" if diff < 0
                    else "On target")
            except (ValueError, TypeError):
                self.variance_from_target = ""

    # ── Weight check ─────────────────────────────────────────────────

    def _check_total_weight_for_cycle(self):
        if not (self.owner_employee and self.performance_cycle):
            return
        total = frappe.db.sql("""
            SELECT SUM(weight) FROM `tabPerformance Goal`
            WHERE owner_employee=%s AND performance_cycle=%s
              AND name != %s AND status NOT IN ('Cancelled')
        """, (self.owner_employee, self.performance_cycle, self.name))[0][0] or 0
        total += flt(self.weight)
        if total > 100:
            frappe.msgprint(
                _("Total goal weight is {0}% (exceeds 100%). Please adjust.").format(
                    round(total, 1)),
                indicator="orange", alert=True)

    # ── Approval workflow ────────────────────────────────────────────

    @frappe.whitelist()
    def approve_goal(self):
        if self.status != "Pending Approval":
            frappe.throw(_("Goal is not pending approval."))
        self.status = "Approved"
        self.approved_by = frappe.db.get_value("Employee",
            {"user_id": frappe.session.user}, "name")
        self.approved_on = nowdate()
        self.save(ignore_permissions=True)
        emp_user = frappe.db.get_value("Employee", self.owner_employee, "user_id")
        if emp_user:
            frappe.sendmail(
                recipients=[emp_user],
                subject=f"Goal Approved: {self.goal_title}",
                message=f"Your goal <b>{self.goal_title}</b> has been approved.")
        return {"success": True}

    @frappe.whitelist()
    def reject_goal(self, reason):
        self.status = "Draft"
        self.rejection_reason = reason
        self.save(ignore_permissions=True)
        emp_user = frappe.db.get_value("Employee", self.owner_employee, "user_id")
        if emp_user:
            frappe.sendmail(
                recipients=[emp_user],
                subject=f"Goal Revision Requested: {self.goal_title}",
                message=(f"Your goal <b>{self.goal_title}</b> requires revision.<br><br>"
                         f"<b>Reason:</b> {reason}"))
        return {"success": True}

    def _notify_manager(self):
        manager = frappe.db.get_value("Employee", self.owner_employee, "reports_to")
        if not manager:
            return
        mgr_user = frappe.db.get_value("Employee", manager, "user_id")
        emp_name = frappe.db.get_value("Employee", self.owner_employee, "employee_name")
        if mgr_user:
            frappe.sendmail(
                recipients=[mgr_user],
                subject=f"Goal for Approval: {emp_name} — {self.goal_title}",
                message=(f"<b>{emp_name}</b> submitted a goal for your approval.<br>"
                         f"<b>Goal:</b> {self.goal_title}<br>"
                         f"<b>Type:</b> {self.goal_type} | "
                         f"<b>Weight:</b> {self.weight}% | "
                         f"<b>Due:</b> {self.due_date}"))